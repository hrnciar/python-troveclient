#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Database v1 Users action implementations"""

from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils
import six

from troveclient.i18n import _


class ListDatabaseUsers(command.Lister):

    _description = _("Lists the users for an instance.")
    columns = ['Name', 'Host', 'Databases']

    def get_parser(self, prog_name):
        parser = super(ListDatabaseUsers, self).get_parser(prog_name)
        parser.add_argument(
            dest='instance',
            metavar='<instance>',
            help=_('ID of the instance.')
        )
        return parser

    def take_action(self, parsed_args):
        db_users = self.app.client_manager.database.users
        items = db_users.list(parsed_args.instance)
        users = items
        while (items.next):
            items = db_users.list(parsed_args.instance, marker=items.next)
            users += items
        for user in users:
            db_names = [db['name'] for db in user.databases]
            user.databases = ', '.join(db_names)
        users = [utils.get_item_properties(u, self.columns) for u in users]
        return self.columns, users


class ShowDatabaseUser(command.ShowOne):

    _description = _("Shows details of a database user of an instance.")

    def get_parser(self, prog_name):
        parser = super(ShowDatabaseUser, self).get_parser(prog_name)
        parser.add_argument(
            'instance',
            metavar='<instance>',
            help=_('ID of the instance.'),
        )
        parser.add_argument(
            'name',
            metavar='<name>',
            help=_('Name of user.'),
        )
        parser.add_argument(
            "--host",
            metavar="<host>",
            help=_("Optional host of user."),
        )
        return parser

    def take_action(self, parsed_args):
        db_users = self.app.client_manager.database.users
        user = db_users.get(parsed_args.instance, parsed_args.name,
                            hostname=parsed_args.host)
        return zip(*sorted(six.iteritems(user._info)))


class DeleteDatabaseUser(command.Command):

    _description = _("Deletes a user from an instance.")

    def get_parser(self, prog_name):
        parser = super(DeleteDatabaseUser, self).get_parser(prog_name)
        parser.add_argument(
            'instance',
            metavar='<instance>',
            help=_('ID or name of the instance.')
        )
        parser.add_argument(
            'name',
            metavar='<name>',
            help=_('Name of user.')
        )
        parser.add_argument(
            '--host',
            metavar='<host>',
            help=_('Optional host of user.')
        )
        return parser

    def take_action(self, parsed_args):
        manager = self.app.client_manager.database
        users = manager.users
        try:
            instance = utils.find_resource(manager.instances,
                                           parsed_args.instance)
            users.delete(instance, parsed_args.name, parsed_args.host)
        except Exception as e:
            msg = (_("Failed to delete user %(user)s: %(e)s")
                   % {'user': parsed_args.name, 'e': e})
            raise exceptions.CommandError(msg)
