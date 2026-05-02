from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..config import settings
from .github_client import GitHubClient
from .incident_store import IncidentStore
from .models import Incident
from .ops import (
    build_incident_bundle,
    create_or_recreate_user,
    delete_user_cascade,
    dispatch_workflow_and_pick_run,
    format_health,
    health_report,
)


@dataclass
class PendingAction:
    action: str
    incident_id: str
    payload: dict


class ConnectAdminBot:
    def __init__(self) -> None:
        if not settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not settings.telegram_admin_ids:
            raise ValueError("TELEGRAM_ADMIN_IDS is required")

        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher()
        self.gh = None
        if settings.github_token and settings.github_repository:
            self.gh = GitHubClient(token=settings.github_token, repository=settings.github_repository)
        self.store = IncidentStore(settings.incident_store_dir)
        self.lock = asyncio.Lock()
        self.pending: dict[int, PendingAction] = {}

        self.dp.message.register(self.help_cmd, Command("start"))
        self.dp.message.register(self.help_cmd, Command("help"))
        self.dp.message.register(self.nodes_reboot, Command("nodes_reboot"))
        self.dp.message.register(self.worker_replace, Command("worker_replace"))
        self.dp.message.register(self.health, Command("health"))
        self.dp.message.register(self.user_create, Command("user_create"))
        self.dp.message.register(self.user_delete, Command("user_delete"))
        self.dp.message.register(self.incident_status_cmd, Command("incident_status"))
        self.dp.message.register(self.propose_cmd, Command("propose"))
        self.dp.message.register(self.agent_cmd, Command("agent"))
        self.dp.message.register(self.approve_cmd, Command("approve"))
        self.dp.message.register(self.deny_cmd, Command("deny"))
        self.dp.message.register(self.retry_cmd, Command("retry"))
        self.dp.message.register(self.handle_text, F.text)
        self.dp.callback_query.register(self.handle_callback, F.data)

    async def run(self) -> None:
        await self.dp.start_polling(self.bot)

    def _is_admin(self, message: Message) -> bool:
        uid = message.from_user.id if message.from_user else 0
        return uid in settings.telegram_admin_ids

    async def _guard(self, message: Message) -> bool:
        if self._is_admin(message):
            return True
        await message.answer("Access denied")
        return False

    async def help_cmd(self, message: Message) -> None:
        if not await self._guard(message):
            return
        await message.answer(
            "Commands:\n"
            "/nodes_reboot\n"
            "/worker_replace\n"
            "/health\n"
            "/user_create <username> [display_name]\n"
            "/user_delete <username>\n"
            "/incident_status <incident_id>\n"
            "/propose <incident_id>\n"
            "/agent <incident_id> <message>\n"
            "/approve <incident_id> [pr_number]\n"
            "/deny <incident_id>\n"
            "/retry <incident_id>"
        )

    async def propose_cmd(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /propose <incident_id>")
            return
        incident = self.store.get(parts[1])
        if not incident:
            await message.answer("Incident not found")
            return
        incident.status = "plan_requested"
        self._mark_decision(
            incident,
            action="propose_fix",
            by_id=message.from_user.id if message.from_user else 0,
            by_username=message.from_user.username if message.from_user else "",
        )
        await self._dispatch_incident_handler(incident, action="propose_fix", user_note="")
        await message.answer(f"Proposal requested for incident {incident.incident_id}")

    async def agent_cmd(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Usage: /agent <incident_id> <message>")
            return
        incident_id = parts[1]
        user_note = parts[2].strip()
        if not user_note:
            await message.answer("Message is empty")
            return
        incident = self.store.get(incident_id)
        if not incident:
            await message.answer("Incident not found")
            return
        dialog = incident.context.get("dialog", [])
        dialog.append(
            {
                "role": "admin",
                "message": user_note,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        incident.context["dialog"] = dialog[-20:]
        incident.status = "plan_iterating"
        self.store.save(incident)
        await self._dispatch_incident_handler(incident, action="propose_fix", user_note=user_note)
        await message.answer(f"Agent iteration requested for incident {incident.incident_id}")

    async def incident_status_cmd(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /incident_status <incident_id>")
            return
        incident = self.store.get(parts[1])
        if not incident:
            await message.answer("Incident not found")
            return
        run_status = "n/a"
        if incident.run_id and self.gh is not None:
            run = self.gh.get_run(incident.run_id)
            run_status = f"{run.get('status')}/{run.get('conclusion')}"
        await message.answer(
            f"incident_id={incident.incident_id}\n"
            f"operation={incident.operation}\n"
            f"status={incident.status}\n"
            f"stage={incident.stage}\n"
            f"summary={incident.summary}\n"
            f"workflow={incident.workflow_url or '-'}\n"
            f"run_state={run_status}"
        )

    async def nodes_reboot(self, message: Message) -> None:
        if not await self._guard(message):
            return
        self.pending[message.from_user.id] = PendingAction(action="nodes_reboot", incident_id="", payload={})
        await message.answer(
            "Risky operation requested: nodes_reboot. Confirm action.",
            reply_markup=self._pending_keyboard("nodes_reboot"),
        )

    async def worker_replace(self, message: Message) -> None:
        if not await self._guard(message):
            return
        self.pending[message.from_user.id] = PendingAction(action="worker_replace", incident_id="", payload={})
        await message.answer(
            "Risky operation requested: worker_replace. Confirm action.",
            reply_markup=self._pending_keyboard("worker_replace"),
        )

    async def health(self, message: Message) -> None:
        if not await self._guard(message):
            return
        result = health_report(settings.telegram_ssh_key_path)
        await message.answer(format_health(result))

    async def user_create(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /user_create <username> [display_name]")
            return
        username = parts[1]
        display_name = " ".join(parts[2:]) if len(parts) > 2 else username.lstrip("@")
        result = create_or_recreate_user(username=username, display_name=display_name, actor="bot")
        if result.ok:
            await message.answer(f"{result.message}\nSubscription: {result.details.get('subscription_url', '-')}")
        else:
            await message.answer(result.message)

    async def user_delete(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /user_delete <username>")
            return
        username = parts[1]
        result = delete_user_cascade(username=username, actor="bot")
        await message.answer(result.message)

    async def approve_cmd(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /approve <incident_id> [pr_number]")
            return
        pr_number = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
        await self._handle_approve(message, parts[1], pr_number=pr_number)

    async def deny_cmd(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /deny <incident_id>")
            return
        incident = self.store.get(parts[1])
        if not incident:
            await message.answer("Incident not found")
            return
        self._mark_decision(incident, action="deny", by_id=message.from_user.id if message.from_user else 0, by_username=message.from_user.username if message.from_user else "")
        await message.answer(f"Denied incident {incident.incident_id}")

    async def retry_cmd(self, message: Message) -> None:
        if not await self._guard(message):
            return
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /retry <incident_id>")
            return
        incident = self.store.get(parts[1])
        if not incident:
            await message.answer("Incident not found")
            return
        self._mark_decision(incident, action="retry", by_id=message.from_user.id if message.from_user else 0, by_username=message.from_user.username if message.from_user else "")
        incident.status = "retry_requested"
        self.store.save(incident)
        await self._dispatch_incident_handler(incident, action="retry")
        await message.answer(f"Retry requested for incident {incident.incident_id}")

    async def handle_text(self, message: Message) -> None:
        if not await self._guard(message):
            return
        text = (message.text or "").strip().lower()
        m = re.search(r"\bapprove\s+([a-f0-9]{8})\b", text)
        if m:
            await self._handle_approve(message, m.group(1))
            return
        m = re.search(r"\bdeny\s+([a-f0-9]{8})\b", text)
        if m:
            incident = self.store.get(m.group(1))
            if incident:
                self._mark_decision(incident, action="deny", by_id=message.from_user.id if message.from_user else 0, by_username=message.from_user.username if message.from_user else "")
                await message.answer(f"Denied incident {incident.incident_id}")
            return
        await self._handle_pending_action(message, text)

    async def _handle_pending_action(self, message: Message, text: str) -> None:
        if not message.from_user:
            return
        pending = self.pending.get(message.from_user.id)
        if not pending:
            return
        if text == f"approve {pending.action}":
            self.pending.pop(message.from_user.id, None)
            if pending.action == "nodes_reboot":
                await self._run_or_incident(message, operation="nodes_reboot", fn=self._op_nodes_reboot, risky=True)
            elif pending.action == "worker_replace":
                await self._run_or_incident(message, operation="worker_replace", fn=self._op_worker_replace, risky=True)
            return
        if text in {f"deny {pending.action}", "cancel"}:
            self.pending.pop(message.from_user.id, None)
            await message.answer(f"Cancelled {pending.action}")

    async def handle_callback(self, callback: CallbackQuery) -> None:
        if not callback.from_user or callback.from_user.id not in settings.telegram_admin_ids:
            await callback.answer("Access denied", show_alert=True)
            return
        data = (callback.data or "").strip()
        try:
            if data.startswith("pending:approve:"):
                action = data.split(":", 2)[2]
                self.pending.pop(callback.from_user.id, None)
                if action == "nodes_reboot":
                    await self._run_or_incident_callback(callback, operation="nodes_reboot", fn=self._op_nodes_reboot)
                elif action == "worker_replace":
                    await self._run_or_incident_callback(callback, operation="worker_replace", fn=self._op_worker_replace)
                await callback.answer("Approved")
                return
            if data.startswith("pending:deny:"):
                action = data.split(":", 2)[2]
                self.pending.pop(callback.from_user.id, None)
                await callback.message.answer(f"Cancelled {action}")
                await callback.answer("Cancelled")
                return
            if data.startswith("incident:retry:"):
                incident_id = data.split(":", 2)[2]
                incident = self.store.get(incident_id)
                if not incident:
                    await callback.answer("Incident not found", show_alert=True)
                    return
                self._mark_decision(incident, action="retry", by_id=callback.from_user.id, by_username=callback.from_user.username or "")
                incident.status = "retry_requested"
                self.store.save(incident)
                await self._dispatch_incident_handler(incident, action="retry")
                await callback.message.answer(f"Retry requested for incident {incident.incident_id}")
                await callback.answer("Retry requested")
                return
            if data.startswith("incident:deny:"):
                incident_id = data.split(":", 2)[2]
                incident = self.store.get(incident_id)
                if not incident:
                    await callback.answer("Incident not found", show_alert=True)
                    return
                self._mark_decision(incident, action="deny", by_id=callback.from_user.id, by_username=callback.from_user.username or "")
                await callback.message.answer(f"Denied incident {incident.incident_id}")
                await callback.answer("Denied")
                return
            if data.startswith("incident:propose:"):
                incident_id = data.split(":", 2)[2]
                incident = self.store.get(incident_id)
                if not incident:
                    await callback.answer("Incident not found", show_alert=True)
                    return
                self._mark_decision(incident, action="propose_fix", by_id=callback.from_user.id, by_username=callback.from_user.username or "")
                incident.status = "plan_requested"
                self.store.save(incident)
                await self._dispatch_incident_handler(incident, action="propose_fix", user_note="")
                await callback.message.answer(f"Plan proposal requested for incident {incident.incident_id}")
                await callback.answer("Proposal requested")
                return
            await callback.answer("Unsupported action", show_alert=True)
        except Exception as exc:  # noqa: BLE001
            await callback.message.answer(f"Callback action failed: {exc}")
            await callback.answer("Failed", show_alert=True)

    async def _handle_approve(self, message: Message, incident_id: str, pr_number: int | None = None) -> None:
        incident = self.store.get(incident_id)
        if not incident:
            await message.answer("Incident not found")
            return
        if pr_number:
            incident.pr_number = pr_number
        decision_action = "approve" if pr_number else "create_dev_pr"
        self._mark_decision(
            incident,
            action=decision_action,
            by_id=message.from_user.id if message.from_user else 0,
            by_username=message.from_user.username if message.from_user else "",
            pr_number=pr_number,
        )
        if pr_number:
            incident.status = "approved"
        else:
            incident.status = "dev_pr_requested"
        self.store.save(incident)
        await self._dispatch_incident_handler(incident, action=decision_action, user_note="")
        await message.answer(
            f"Approved incident {incident.incident_id}, handler workflow dispatched (action={decision_action})"
        )

    async def _run_or_incident(self, message: Message, operation: str, fn, risky: bool = False) -> None:
        if self.lock.locked():
            await message.answer("Another infrastructure operation is running. Try later.")
            return

        async with self.lock:
            try:
                if self.gh is None:
                    raise RuntimeError("GitHub integration is not configured (GITHUB_TOKEN/GITHUB_REPOSITORY)")
                run_id = await fn()
                await message.answer(f"{operation} started. Run: {self.gh.run_url(run_id)}")
                asyncio.create_task(self._watch_run(operation=operation, run_id=run_id, chat_id=message.chat.id))
            except Exception as exc:  # noqa: BLE001
                incident = self.store.create(
                    operation=operation,
                    stage="dispatch",
                    summary=str(exc),
                    context={"risky": risky},
                )
                bundle = build_incident_bundle(
                    incident_id=incident.incident_id,
                    operation=operation,
                    stage=incident.stage,
                    error=incident.summary,
                )
                incident.context["bundle"] = bundle
                self.store.save(incident)
                await message.answer(
                    f"Operation failed: {operation}\n"
                    f"incident_id={incident.incident_id}\n"
                    f"reason={incident.summary}\n"
                    f"Use /retry {incident.incident_id} or /propose {incident.incident_id}",
                    reply_markup=self._incident_keyboard(incident.incident_id),
                )

    async def _run_or_incident_callback(self, callback: CallbackQuery, operation: str, fn) -> None:
        if self.lock.locked():
            await callback.message.answer("Another infrastructure operation is running. Try later.")
            return
        async with self.lock:
            try:
                if self.gh is None:
                    raise RuntimeError("GitHub integration is not configured (GITHUB_TOKEN/GITHUB_REPOSITORY)")
                run_id = await fn()
                await callback.message.answer(f"{operation} started. Run: {self.gh.run_url(run_id)}")
                asyncio.create_task(self._watch_run(operation=operation, run_id=run_id, chat_id=callback.message.chat.id))
            except Exception as exc:  # noqa: BLE001
                incident = self.store.create(
                    operation=operation,
                    stage="dispatch",
                    summary=str(exc),
                    context={"risky": True},
                )
                bundle = build_incident_bundle(
                    incident_id=incident.incident_id,
                    operation=operation,
                    stage=incident.stage,
                    error=incident.summary,
                )
                incident.context["bundle"] = bundle
                self.store.save(incident)
                await callback.message.answer(
                    f"Operation failed: {operation}\n"
                    f"incident_id={incident.incident_id}\n"
                    f"reason={incident.summary}",
                    reply_markup=self._incident_keyboard(incident.incident_id),
                )

    async def _watch_run(self, operation: str, run_id: int, chat_id: int) -> None:
        for _ in range(90):
            await asyncio.sleep(20)
            run = self.gh.get_run(run_id)
            status = run.get("status")
            conclusion = run.get("conclusion")
            if status != "completed":
                continue
            if conclusion == "success":
                await self.bot.send_message(chat_id, f"{operation} completed successfully: {self.gh.run_url(run_id)}")
                return

            fail_summary = f"run finished with conclusion={conclusion}"
            job_url = ""
            jobs = self.gh.get_run_jobs(run_id)
            for job in jobs:
                if job.get("conclusion") == "failure":
                    job_id = int(job.get("id"))
                    job_url = self.gh.job_url(run_id, job_id)
                    steps = job.get("steps") or []
                    failed_step = next((s for s in steps if s.get("conclusion") == "failure"), None)
                    step_name = failed_step.get("name") if failed_step else "unknown-step"
                    fail_summary = f"job={job.get('name')} step={step_name} conclusion={conclusion}"
                    break

            incident = self.store.create(
                operation=operation,
                stage="workflow",
                summary=fail_summary,
                context={"run_id": run_id, "workflow_url": self.gh.run_url(run_id), "job_url": job_url},
            )
            incident.run_id = run_id
            incident.workflow_url = self.gh.run_url(run_id)
            self.store.save(incident)
            await self.bot.send_message(
                chat_id,
                (
                    f"Incident detected for {operation}\n"
                    f"incident_id={incident.incident_id}\n"
                    f"run={incident.workflow_url}\n"
                    f"job={job_url or '-'}\n"
                    f"summary={incident.summary}\n"
                    f"Use /retry {incident.incident_id} or /propose {incident.incident_id}"
                ),
                reply_markup=self._incident_keyboard(incident.incident_id),
            )
            return

    async def _op_nodes_reboot(self) -> int:
        return await dispatch_workflow_and_pick_run(
            self.gh,
            workflow_file="ops-nodes-reboot.yml",
            inputs={"reason": "telegram_bot"},
        )

    async def _op_worker_replace(self) -> int:
        return await dispatch_workflow_and_pick_run(
            self.gh,
            workflow_file="ops-worker-bluegreen.yml",
            inputs={"old_worker_name": settings.worker_replace_old_node_name},
        )

    async def _dispatch_incident_handler(self, incident: Incident, action: str, user_note: str = "") -> None:
        inputs = {
            "incident_id": incident.incident_id,
            "action": action,
            "operation": incident.operation,
            "run_id": str(incident.run_id or ""),
            "pr_number": str(incident.pr_number or ""),
            "summary": incident.summary,
            "user_note": user_note,
        }
        if self.gh is None:
            raise RuntimeError("GitHub integration is not configured for incident handler")
        self.gh.dispatch_workflow("incident-handler.yml", ref="main", inputs=inputs)

    def _mark_decision(
        self,
        incident: Incident,
        action: str,
        by_id: int,
        by_username: str,
        pr_number: int | None = None,
    ) -> None:
        if action == "deny":
            incident.status = "denied"
        incident.context["decision"] = {
            "by_id": by_id,
            "by_username": by_username,
            "at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "pr_number": pr_number or "",
        }
        self.store.save(incident)

    def _pending_keyboard(self, action: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Approve", callback_data=f"pending:approve:{action}"),
                    InlineKeyboardButton(text="Cancel", callback_data=f"pending:deny:{action}"),
                ]
            ]
        )

    def _incident_keyboard(self, incident_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Retry", callback_data=f"incident:retry:{incident_id}"),
                    InlineKeyboardButton(text="Propose Plan", callback_data=f"incident:propose:{incident_id}"),
                    InlineKeyboardButton(text="Deny", callback_data=f"incident:deny:{incident_id}"),
                ]
            ]
        )


async def _amain() -> None:
    bot = ConnectAdminBot()
    await bot.run()


def run_bot() -> None:
    asyncio.run(_amain())
