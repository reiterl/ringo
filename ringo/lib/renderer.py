import logging
from mako.lookup import TemplateLookup
from ringo import template_dir

template_lookup = TemplateLookup(directories=[template_dir],
                                 module_directory='/tmp/ringo_modules')

log = logging.getLogger(__name__)


class Renderer(object):
    """Baseclass for all renderers"""

    def __init__(self):
        """Initialize renderer"""
        pass

    def render(self):
        """Initialize renderer"""
        pass


class ListRenderer(Renderer):
    """Docstring for ListRenderer """

    def __init__(self, clazz):
        """@todo: to be defined """
        Renderer.__init__(self)
        self.clazz = clazz
        self.template = template_lookup.get_template("internal/list.mako")

    def render(self, items):
        """Initialize renderer"""
        values = {'items': items,
                  'headers': self.clazz._table_fields}
        return self.template.render(**values)


class DialogRenderer(Renderer):
    """Renderer for Dialogs"""

    def __init__(self, request, item, action, title=None, body=None):
        """Renders a renderered dialog for the requested action on the
        given item. If not header or body is provided the dialog will
        have a default message.

        :request: The current request
        :item: The item for which the item should be confirmed.
        :action: The actions which must be confirmend.
        :header: Custom text for the header of the dialog
        :body: Custom text for the body of the dialog.

        """
        Renderer.__init__(self)

        self._request = request
        self._item = item
        self._action = action
        self._title = title
        self._body = body


class ConfirmDialogRenderer(DialogRenderer):
    """Docstring for ConfirmDialogRenderer """

    def __init__(self, request, item, action, title=None, body=None):
        """@todo: to be defined """
        DialogRenderer.__init__(self, request, item, action, title, body)
        self.template = template_lookup.get_template("internal/confirm.mako")

    def render(self):
        values = {}
        values['icon'] = self._request.static_url(
            'ringo:static/images/icons/32x32/dialog-warning.png')
        values['header'] = "Confirm %s" % self._action
        values['body'] = self._render_body()
        values['action'] = self._action.capitalize()
        values['ok_url'] = self._request.current_route_url()
        values['cancel_url'] = self._request.referrer
        return self.template.render(**values)

    def _render_body(self):
        out = []
        item_label = self._item.get_item_modul().get_label()
        out.append("Do you really want to %s"
                   " the following %s items?" % (self._action, item_label))
        out.append("<br>")
        out.append("<ol>")
        if isinstance(self._item, list):
            items = self._item
        else:
            items = [self._item]
        for item in items:
            out.append("<li>")
            out.append(unicode(item))
            out.append("</li>")
        out.append("</ol>")
        out.append('Please press "%s" to %s the item.'
                   ' Press "Cancel" to cancel the action.'
                   % (self._action.capitalize(), self._action))

        return "".join(out)
