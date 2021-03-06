# SCP-079-LONG - Control super long messages
# Copyright (C) 2019-2020 SCP-079 <https://scp-079.org>
#
# This file is part of SCP-079-LONG.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import re
from copy import deepcopy
from subprocess import run, PIPE

from telegram import Update
from telegram.ext import CallbackContext, Dispatcher, Filters, PrefixHandler

from .. import glovar
from ..functions.channel import get_debug_text, share_data
from ..functions.etc import code, delay, general_link, get_command_context, get_command_type, get_int, get_now
from ..functions.etc import get_readable_time, lang, thread, mention_id
from ..functions.file import save
from ..functions.filters import authorized_group, captcha_group, from_user, is_class_c, test_group
from ..functions.group import get_config_text
from ..functions.telegram import delete_message, get_group_info, send_message, send_report_message

# Enable logging
logger = logging.getLogger(__name__)


def add_command_handlers(dispatcher: Dispatcher) -> bool:
    # Add command handlers
    try:
        # /config
        dispatcher.add_handler(PrefixHandler(
            prefix=glovar.prefix,
            command=["config"],
            callback=config,
            filters=(Filters.update.messages & Filters.group
                     & ~captcha_group & ~test_group & authorized_group
                     & from_user)
        ))

        # /config_long
        dispatcher.add_handler(PrefixHandler(
            prefix=glovar.prefix,
            command=[f"config_{glovar.sender.lower()}"],
            callback=config_directly,
            filters=(Filters.update.messages & Filters.group
                     & ~captcha_group & ~test_group & authorized_group
                     & from_user)
        ))

        # /long
        dispatcher.add_handler(PrefixHandler(
            prefix=glovar.prefix,
            command=["long", "l"],
            callback=long,
            filters=(Filters.update.messages & Filters.group
                     & from_user)
        ))

        # /version
        dispatcher.add_handler(PrefixHandler(
            prefix=glovar.prefix,
            command=["version"],
            callback=version,
            filters=(Filters.update.messages & Filters.group
                     & test_group
                     & from_user)
        ))

        return True
    except Exception as e:
        logger.warning(f"Add command handlers error: {e}", exc_info=True)

    return False


def config(update: Update, context: CallbackContext) -> bool:
    # Request CONFIG session

    if not context or not context.bot:
        return True

    if not update or not update.effective_message:
        return True

    # Basic data
    client = context.bot
    message = update.effective_message
    gid = message.chat.id
    mid = message.message_id

    try:
        # Check permission
        if not is_class_c(None, message):
            return True

        # Check command format
        command_type = get_command_type(message)

        if not command_type or not re.search(f"^{glovar.sender}$", command_type, re.I):
            return True

        now = get_now()

        # Check the config lock
        if now - glovar.configs[gid]["lock"] < 310:
            return True

        # Set lock
        glovar.configs[gid]["lock"] = now
        save("configs")

        # Ask CONFIG generate a config session
        group_name, group_link = get_group_info(client, message.chat)
        share_data(
            client=client,
            receivers=["CONFIG"],
            action="config",
            action_type="ask",
            data={
                "project_name": glovar.project_name,
                "project_link": glovar.project_link,
                "group_id": gid,
                "group_name": group_name,
                "group_link": group_link,
                "user_id": message.from_user.id,
                "config": glovar.configs[gid],
                "default": glovar.default_config
            }
        )

        # Send debug message
        text = get_debug_text(client, message.chat)
        text += (f"{lang('admin_group')}{lang('colon')}{code(message.from_user.id)}\n"
                 f"{lang('action')}{lang('colon')}{code(lang('config_create'))}\n")
        thread(send_message, (client, glovar.debug_channel_id, text))

        return True
    except Exception as e:
        logger.warning(f"Config error: {e}", exc_info=True)
    finally:
        if is_class_c(None, message):
            delay(3, delete_message, [client, gid, mid])
        else:
            thread(delete_message, (client, gid, mid))

    return False


def config_directly(update: Update, context: CallbackContext) -> bool:
    # Config the bot directly

    if not context or not context.bot:
        return True

    if not update or not update.effective_message:
        return True

    # Basic data
    client = context.bot
    message = update.effective_message
    gid = message.chat.id
    mid = message.message_id

    try:
        # Check permission
        if not is_class_c(None, message):
            return True

        aid = message.from_user.id
        success = True
        reason = lang("config_updated")
        new_config = deepcopy(glovar.configs[gid])
        text = f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"

        # Check command format
        command_type, command_context = get_command_context(message)

        if command_type:
            if command_type == "show":
                text += f"{lang('action')}{lang('colon')}{code(lang('config_show'))}\n"
                text += get_config_text(new_config)
                thread(send_report_message, (30, client, gid, text))
                thread(delete_message, (client, gid, mid))
                return True

            now = get_now()

            # Check the config lock
            if now - new_config["lock"] > 310:
                if command_type == "default":
                    new_config = deepcopy(glovar.default_config)
                else:
                    if command_context:
                        if command_type in {"delete", "restrict"}:
                            if command_context == "off":
                                new_config[command_type] = False
                            elif command_context == "on":
                                new_config[command_type] = True
                            else:
                                success = False
                                reason = lang("command_para")
                        elif command_type == "limit":
                            limit = get_int(command_context)

                            if 500 <= limit <= 10000 and limit in set(range(500, 10500, 500)):
                                new_config["limit"] = limit
                            else:
                                success = False
                                reason = lang("command_para")
                        else:
                            success = False
                            reason = lang("command_type")
                    else:
                        success = False
                        reason = lang("command_lack")

                    if success:
                        new_config["default"] = False
            else:
                success = False
                reason = lang("config_locked")
        else:
            success = False
            reason = lang("command_usage")

        if success and new_config != glovar.configs[gid]:
            # Save new config
            glovar.configs[gid] = new_config
            save("configs")

            # Send debug message
            debug_text = get_debug_text(client, message.chat)
            debug_text += (f"{lang('admin_group')}{lang('colon')}{code(message.from_user.id)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                           f"{lang('more')}{lang('colon')}{code(f'{command_type} {command_context}')}\n")
            thread(send_message, (client, glovar.debug_channel_id, debug_text))

        text += (f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                 f"{lang('status')}{lang('colon')}{code(reason)}\n")
        thread(send_report_message, ((lambda x: 10 if x else 5)(success), client, gid, text))

        return True
    except Exception as e:
        logger.warning(f"Config directly error: {e}", exc_info=True)
    finally:
        thread(delete_message, (client, gid, mid))

    return False


def long(update: Update, context: CallbackContext) -> bool:
    # Fore to check long messages
    try:
        client = context.bot
        message = update.effective_message

        # Delete the command
        gid = message.chat.id
        mid = message.message_id
        thread(delete_message, (client, gid, mid))

        return True
    except Exception as e:
        logger.warning(f"Long error: {e}", exc_info=True)

    return False


def version(update: Update, context: CallbackContext) -> bool:
    # Check the program's version
    result = False

    try:
        client = context.bot
        message = update.edited_message or update.message

        # Basic data
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id

        # Get command type
        command_type = get_command_type(message)

        # Check the command type
        if command_type and command_type.upper() != glovar.sender:
            return False

        # Version info
        git_change = bool(run("git diff-index HEAD --", stdout=PIPE, shell=True).stdout.decode().strip())
        git_date = run("git log -1 --format='%at'", stdout=PIPE, shell=True).stdout.decode()
        git_date = get_readable_time(get_int(git_date), "%Y/%m/%d %H:%M:%S")
        git_hash = run("git rev-parse --short HEAD", stdout=PIPE, shell=True).stdout.decode()
        get_hash_link = f"https://github.com/scp-079/scp-079-{glovar.sender.lower()}/commit/{git_hash}"
        command_date = get_readable_time(int(message.date.strftime("%s")), "%Y/%m/%d %H:%M:%S")

        # Generate the text
        text = (f"{lang('admin')}{lang('colon')}{mention_id(aid)}\n\n"
                f"{lang('project')}{lang('colon')}{code(glovar.sender)}\n"
                f"{lang('version')}{lang('colon')}{code(glovar.version)}\n"
                f"{lang('本地修改')}{lang('colon')}{code(git_change)}\n"
                f"{lang('哈希值')}{lang('colon')}{general_link(git_hash, get_hash_link)}\n"
                f"{lang('提交时间')}{lang('colon')}{code(git_date)}\n"
                f"{lang('命令发送时间')}{lang('colon')}{code(command_date)}\n")

        # Send the report message
        result = send_message(client, cid, text, mid)
    except Exception as e:
        logger.warning(f"Version error: {e}", exc_info=True)

    return result
