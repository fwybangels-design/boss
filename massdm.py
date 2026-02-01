# mass_dm_bot.py
# WARNING: This file intentionally uses placeholder tokens. Do NOT paste real tokens into public chats.
# Replace the placeholders with your real tokens locally if you choose to run this file.
# NOTE: Mass-DMing large numbers of users may violate Discord's Terms of Service. Use responsibly.

import time
import asyncio
from discord.ext import commands
import discord

# Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Bot (controller)
bot = commands.Bot(command_prefix="!", intents=intents)

# TOKENS: Replace these placeholders locally with your actual tokens if you must run the bot.
# The first token is the controller (receives commands). The rest are sender tokens for round-robin.
TOKENS = [
    "",  # controller (keeps command behavior)
    "",
    "",
]

# Globals used by mdm and supervision
sender_clients = []   # active discord.Client objects (supervisor appends them)
sender_tasks = []     # supervision tasks
sender_meta = {}      # maps client -> { token_index, token, dead, restarts, started_once }
dm_active = False

def user_label_from_user_obj(user):
    if user is None:
        return "unknown"
    name = getattr(user, "name", None)
    disc = getattr(user, "discriminator", None)
    uid = getattr(user, "id", None)
    if name is None:
        return f"unknown ({uid})"
    if disc is not None and disc != "":
        return f"{name}#{disc}"
    return f"{name} ({uid})"

@bot.event
async def on_ready():
    print(f'Controller logged in as {bot.user} ({bot.user.id})')

# --- Supervision: start sender clients with limited retries and avoid noisy reconnects ---

async def _supervise_sender(token: str, token_index: int, max_restarts: int = 3):
    """
    Start a discord.Client for a sender token with supervision:
    - Use reconnect=False to avoid auto reconnect loops.
    - Mark token dead on LoginFailure or HTTP 401.
    - Retry transient errors up to max_restarts with exponential backoff.
    - Log only state-changes to reduce noise.
    """
    client = discord.Client(intents=intents)
    sender_clients.append(client)
    sender_meta[client] = {
        "token_index": token_index,
        "token": token,
        "dead": False,
        "restarts": 0,
        "started_once": False,
    }
    meta = sender_meta[client]

    # on_ready handler to announce once
    @client.event
    async def _on_ready(c=client):
        try:
            label = user_label_from_user_obj(getattr(c, "user", None))
            print(f"[sender #{token_index}] logged in as {label}")
        except Exception:
            print(f"[sender #{token_index}] logged in (label unavailable)")
        meta["started_once"] = True

    # Supervise loop
    while not meta["dead"] and meta["restarts"] <= max_restarts:
        try:
            # start client without auto-reconnect to avoid noisy retry loops
            await client.start(token, reconnect=False)
            # If start returns cleanly (rare), break out
            print(f"[sender #{token_index}] client.start returned cleanly.")
            break
        except discord.LoginFailure:
            meta["dead"] = True
            print(f"[sender #{token_index}] token invalid/revoked (LoginFailure). Marking token dead.")
            break
        except discord.HTTPException as e:
            # try to detect 401-like unauthorized errors (best-effort)
            status = getattr(e, "status", None)
            if status == 401 or ("401" in str(e) or "unauthorized" in str(e).lower()):
                meta["dead"] = True
                print(f"[sender #{token_index}] HTTP 401/Unauthorized detected. Marking token dead.")
                break

            meta["restarts"] += 1
            if meta["restarts"] > max_restarts:
                print(f"[sender #{token_index}] transient HTTP errors; reached max restarts ({max_restarts}). Stopping retries.")
                break
            backoff = min(60, 2 ** meta["restarts"])
            print(f"[sender #{token_index}] HTTPException: {e}. Restarting after {backoff}s (attempt {meta['restarts']}/{max_restarts}).")
            await asyncio.sleep(backoff)
            continue
        except Exception as e:
            meta["restarts"] += 1
            if meta["restarts"] > max_restarts:
                print(f"[sender #{token_index}] unexpected error and max restarts reached: {e}. Will stop retrying.")
                break
            backoff = min(60, 2 ** meta["restarts"])
            print(f"[sender #{token_index}] unexpected error: {e}. Restarting after {backoff}s (attempt {meta['restarts']}/{max_restarts}).")
            await asyncio.sleep(backoff)
            continue

    # Cleanup: try to close the client if appropriate
    try:
        if not getattr(client, "is_closed", lambda: True)():
            await client.close()
    except Exception:
        pass

    if meta["dead"]:
        print(f"[sender #{token_index}] token marked dead; supervisor ending for this token.")
    else:
        print(f"[sender #{token_index}] supervision ended for this token.")

async def start_all_senders_supervised(sender_tokens):
    """Fire off supervised tasks for each sender token (non-blocking)."""
    for i, tok in enumerate(sender_tokens, start=1):
        task = asyncio.create_task(_supervise_sender(tok, token_index=i, max_restarts=3))
        sender_tasks.append(task)
        # small stagger to avoid simultaneous starts
        await asyncio.sleep(0.15)

# --- The mdm command (only small behavior changes: mention on first line; dynamic sender pruning) ---

@bot.command()
@commands.has_permissions(administrator=True)
async def mdm(ctx, *, message: str):
    """
    Send a DM to every member in the server.
    Changes:
      - Each DM starts with the recipient mention on its own line, then the message text.
      - During a run, sender clients that die/unready are pruned from rotation so the run continues quietly.
    """
    global dm_active
    if dm_active:
        await ctx.send("A mass DM operation is already in progress.")
        return

    dm_active = True
    try:
        await ctx.message.delete()
    except Exception:
        pass

    sent_count = 0
    failed_count = 0
    start_time = time.time()
    controller_label = user_label_from_user_obj(getattr(bot, "user", None))

    status_message = await ctx.send(
        f"**Mass DM Operation Started**\n"
        f"Message: {message}\n"
        f"Total Members: {len(ctx.guild.members)}\n"
        f"Time Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}\n"
        f"----------------------------------------\n"
        f"DMing: N/A\n"
        f"Status: Pending\n"
        f"People DMed: {sent_count}\n"
        f"People Failed to DM: {failed_count}\n"
        f"Time Elapsed: 0 seconds"
    )

    # Wait a short period for sender clients to become ready (if any)
    if sender_clients:
        for _ in range(20):
            if all(getattr(c, "is_ready", lambda: False)() or sender_meta.get(c, {}).get("dead", False) for c in sender_clients):
                break
            await asyncio.sleep(1)

    # Open log file
    with open("massdm.txt", "a", encoding="utf-8") as log_file:
        log_file.write(f"\nMass DM started by {ctx.author} in {ctx.guild.name} ({ctx.guild.id})\n")
        log_file.write(f"Message: {message}\n\n")

        # Optionally DM a specific user first (your ID here if desired)
        YOUR_USER_ID = 1437183561756180580
        you_member = ctx.guild.get_member(YOUR_USER_ID)
        if you_member and not you_member.bot:
            label = controller_label
            log_message = f"{label}  Attempting to DM {you_member} ({you_member.id})... "
            print(log_message, end="")
            log_file.write(log_message)
            try:
                # Tiny change: mention on first line, then message
                await you_member.send(content=f"{you_member.mention}\n{message}")
                sent_count += 1
                success_message = "Success!"
                print(success_message)
                log_file.write(success_message + "\n")

                elapsed_time = int(time.time() - start_time)
                await status_message.edit(content=(
                    f"**Mass DM Operation In Progress**\n"
                    f"Message: {message}\n"
                    f"Total Members: {len(ctx.guild.members)}\n"
                    f"Time Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}\n"
                    f"----------------------------------------\n"
                    f"DMing: {you_member} ({you_member.id}) [YOU - FIRST]\n"
                    f"Status: Success\n"
                    f"People DMed: {sent_count}\n"
                    f"People Failed to DM: {failed_count}\n"
                    f"Time Elapsed: {elapsed_time} seconds"
                ))
            except Exception as e:
                failed_count += 1
                error_message = f"Failed: {e}"
                print(error_message)
                log_file.write(error_message + "\n")
            # Removed delay for faster DM speed

        # Build initial available_senders list (only clients that are ready and in the guild and not marked dead)
        available_senders = [
            s for s in sender_clients
            if getattr(s, "is_ready", lambda: False)() and s.get_guild(ctx.guild.id) is not None and not sender_meta.get(s, {}).get("dead", False)
        ]

        # Pre-run status checks and warnings
        unready_senders = [c for c in sender_clients if not getattr(c, "is_ready", lambda: False)()]
        not_in_guild_senders = [c for c in sender_clients if getattr(c, "is_ready", lambda: False)() and c.get_guild(ctx.guild.id) is None]
        if unready_senders or not_in_guild_senders:
            parts = []
            if unready_senders:
                parts.append(f"{len(unready_senders)} sender(s) not ready")
            if not_in_guild_senders:
                parts.append(f"{len(not_in_guild_senders)} sender(s) not in this guild")
            warning = "; ".join(parts)
            try:
                await ctx.send(f"Warning: {warning}. These will be ignored for this run. Proceeding with available senders (controller fallback if none).", delete_after=20)
            except Exception:
                pass
            log_file.write("WARN: " + warning + "\n")
            print("WARN:", warning)

        # Prepare sender usage tracker
        sender_usage = {}
        for s in sender_clients:
            if getattr(s, "is_ready", lambda: False)():
                user = getattr(s, "user", None)
                label = user_label_from_user_obj(user)
            else:
                label = "not-ready"
            sender_usage[s] = {"label": label, "used": 0, "skipped_reason": None}
        for s in unready_senders:
            sender_usage[s]["skipped_reason"] = "not_ready"
        for s in not_in_guild_senders:
            sender_usage[s]["skipped_reason"] = "not_in_guild"
        for s in sender_clients:
            if sender_meta.get(s, {}).get("dead"):
                sender_usage[s]["skipped_reason"] = "dead_token"

        client_index = 0
        total_senders = len(available_senders)

        # Main send loop
        for member in ctx.guild.members:
            if not dm_active:
                break
            if member.bot or member == bot.user:
                continue
            if member.id == YOUR_USER_ID:
                continue

            # Dynamic sender selection: pick next usable sender, prune unusable ones on the fly
            used_sender = None
            used_label = controller_label

            if total_senders > 0 and available_senders:
                attempts = 0
                # try up to current total_senders candidates
                while attempts < total_senders:
                    candidate = available_senders[client_index % total_senders]
                    client_index += 1
                    attempts += 1

                    # Skip candidate if marked dead by supervisor
                    if sender_meta.get(candidate, {}).get("dead", False):
                        try:
                            available_senders.remove(candidate)
                        except ValueError:
                            pass
                        total_senders = len(available_senders)
                        continue

                    # Skip if not ready
                    if not getattr(candidate, "is_ready", lambda: False)():
                        try:
                            available_senders.remove(candidate)
                        except ValueError:
                            pass
                        total_senders = len(available_senders)
                        continue

                    # Skip if not in guild
                    if candidate.get_guild(ctx.guild.id) is None:
                        try:
                            available_senders.remove(candidate)
                        except ValueError:
                            pass
                        total_senders = len(available_senders)
                        continue

                    # candidate is usable
                    used_sender = candidate
                    used_label = user_label_from_user_obj(getattr(used_sender, "user", None))
                    break

            log_message = f"{used_label}  Attempting to DM {member} ({member.id})... "
            print(log_message, end="")
            log_file.write(log_message)

            try:
                # Tiny change: mention on first line, then message
                if used_sender is not None:
                    user = await used_sender.fetch_user(member.id)
                    await user.send(content=f"{member.mention}\n{message}")
                    sender_usage[used_sender]["used"] += 1
                    log_file.write(f"Sent by {sender_usage[used_sender]['label']}\n")
                else:
                    await member.send(content=f"{member.mention}\n{message}")
                    log_file.write("Sent by controller\n")

                sent_count += 1
                print("Success!")
                log_file.write("Success!\n")
            except Exception as e:
                failed_count += 1
                error_message = f"Failed: {e}"
                print(error_message)
                log_file.write(error_message + "\n")

                # If this failure looks like the token/client is now unauthorized or otherwise unrecoverable,
                # mark it dead and prune from available_senders so retries stop.
                try:
                    msg = str(e).lower()
                    if used_sender is not None and ("401" in msg or "unauthorized" in msg or isinstance(e, discord.LoginFailure)):
                        if sender_meta.get(used_sender):
                            sender_meta[used_sender]["dead"] = True
                        try:
                            available_senders.remove(used_sender)
                        except Exception:
                            pass
                        total_senders = len(available_senders)
                        sender_usage[used_sender]["skipped_reason"] = "dead_token_during_run"
                except Exception:
                    pass

            # Update status message only every 10 DMs to reduce API calls and speed up operation
            if (sent_count + failed_count) % 10 == 0:
                elapsed_time = int(time.time() - start_time)
                try:
                    await status_message.edit(content=(
                        f"**Mass DM Operation In Progress**\n"
                        f"Message: {message}\n"
                        f"Total Members: {len(ctx.guild.members)}\n"
                        f"Time Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}\n"
                        f"----------------------------------------\n"
                        f"DMing: {member} ({member.id})\n"
                        f"Status: {'Success' if member.dm_channel else 'Failed'}\n"
                        f"People DMed: {sent_count}\n"
                        f"People Failed to DM: {failed_count}\n"
                        f"Time Elapsed: {elapsed_time} seconds"
                    ))
                except Exception:
                    pass

            # Minimal delay for maximum speed - can send ~20 DMs per second
            await asyncio.sleep(0.05)

        # Build sender report (used vs skipped)
        used_list = []
        available_but_unused = []
        skipped_list = []
        for s, info in sender_usage.items():
            label = info["label"]
            if info["skipped_reason"] is not None:
                skipped_list.append(f"{label} - reason={info['skipped_reason']}")
            else:
                if info["used"] > 0:
                    used_list.append(f"{label} - messages_sent={info['used']}")
                else:
                    available_but_unused.append(f"{label} - messages_sent=0")

        summary_message = (
            f"\n**Mass DM Operation Completed**\n"
            f"Total Members: {len(ctx.guild.members)}\n"
            f"People DMed: {sent_count}\n"
            f"People Failed to DM: {failed_count}\n"
            f"Total Time Taken: {int(time.time() - start_time)} seconds\n"
            f"\nSenders USED:\n" + ("\n".join(used_list) if used_list else "None") +
            f"\n\nAvailable but NOT USED (no sends during run):\n" + ("\n".join(available_but_unused) if available_but_unused else "None") +
            f"\n\nSenders SKIPPED (unready or not in guild or dead):\n" + ("\n".join(skipped_list) if skipped_list else "None") + "\n"
        )
        print(summary_message)
        log_file.write(summary_message)

    # DM the command invoker with final counts (best-effort)
    try:
        await ctx.author.send(f'Message sent to {sent_count} members. Failed to send to {failed_count} members.')
    except Exception:
        pass

    dm_active = False

@mdm.error
async def mdm_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You need Administrator permissions to use this command.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `!mdm <message>`", delete_after=5)
    else:
        await ctx.send(f"An error occurred: {error}", delete_after=5)

# mdme to stop a running mass-DM
@bot.command()
@commands.has_permissions(administrator=True)
async def mdme(ctx):
    global dm_active
    if not dm_active:
        await ctx.send("No mass DM operation is currently in progress.")
        return
    dm_active = False
    await ctx.send("The mass DM operation has been halted.")

@mdme.error
async def mdme_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You need Administrator permissions to use this command.")

# --- Main entrypoint: supervised sender startup + controller start ---

async def main():
    controller_token = TOKENS[0] if TOKENS else None
    sender_tokens = TOKENS[1:] if len(TOKENS) > 1 else []

    # Start supervised sender clients in background
    if sender_tokens:
        await start_all_senders_supervised(sender_tokens)

    # Allow a short window for senders to initialize and print ready states
    if sender_tasks:
        await asyncio.sleep(3)

    # Start the controller bot (blocks until stopped)
    try:
        if controller_token:
            await bot.start(controller_token)
        else:
            print("No controller token provided in TOKENS.")
    finally:
        # On shutdown, ensure sender clients are closed and supervise tasks cancelled
        for c in list(sender_clients):
            try:
                if sender_meta.get(c):
                    sender_meta[c]["dead"] = True
                await c.close()
            except Exception:
                pass
        for t in sender_tasks:
            if not t.done():
                t.cancel()
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
