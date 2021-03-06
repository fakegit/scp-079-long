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

from telegram import Bot

from .. import glovar
from .etc import code, lang, thread
from .file import save
from .telegram import leave_chat

# Enable logging
logger = logging.getLogger(__name__)


def get_config_text(config: dict) -> str:
    # Get config text
    result = ""
    try:
        # Basic
        default_text = (lambda x: lang("default") if x else lang("custom"))(config.get("default"))
        delete_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get("delete"))
        restrict_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get("restrict"))
        result += (f"{lang('config')}{lang('colon')}{code(default_text)}\n"
                   f"{lang('delete')}{lang('colon')}{code(delete_text)}\n"
                   f"{lang('restrict')}{lang('colon')}{code(restrict_text)}\n")

        # Limit
        result += f"{lang('long_limit')}{lang('colon')}{code(config.get('limit'))}\n"
    except Exception as e:
        logger.warning(f"Get config text error: {e}", exc_info=True)

    return result


def leave_group(client: Bot, gid: int) -> bool:
    # Leave a group, clear it's data
    try:
        glovar.left_group_ids.add(gid)
        save("left_group_ids")
        thread(leave_chat, (client, gid))

        glovar.admin_ids.pop(gid, None)
        save("admin_ids")

        glovar.trust_ids.pop(gid, set())
        save("trust_ids")

        glovar.configs.pop(gid, None)
        save("configs")

        glovar.declared_message_ids.pop(gid, set())
        glovar.recorded_ids.pop(gid, set())

        return True
    except Exception as e:
        logger.warning(f"Leave group error: {e}", exc_info=True)

    return False
