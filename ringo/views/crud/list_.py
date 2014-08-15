import uuid
import logging
from ringo.model.base import BaseFactory
from ringo.model.user import User
from ringo.lib.security import has_permission
from ringo.lib.renderer import (
    ListRenderer
)
from ringo.views.request import (
    handle_params,
    handle_history
)
from ringo.views.crud.export import _handle_export_request
from ringo.views.crud.delete import _handle_delete_request

log = logging.getLogger(__name__)


def handle_sorting(clazz, request):
    """Return a tuple of *fieldname* and *sortorder* (asc, desc). The
    sorting is determined in the follwoing order: First try to get the
    sorting from the current request (GET-Param). If there are no
    sorting params try to get the params saved in the session or if
    requested from a saved search. As last
    fallback use the default sorting for the table.
    """
    name = clazz.__tablename__

    # Default sorting options
    default_field = clazz.get_table_config().get_default_sort_column()
    default_order = clazz.get_table_config().get_default_sort_order()

    # Get sorting from the session. If there is no saved sorting use the
    # default value.
    field = request.session.get('%s.list.sort_field' % name, default_field)
    order = request.session.get('%s.list.sort_order' % name, default_order)

    # Get saved sorting from the the saved search.
    saved_search_id = request.params.get('saved')
    if saved_search_id:
        searches_dic = request.user.settings.get('searches', {})
        if searches_dic:
            search = searches_dic.get(name)
            if search:
                field, order = search.get(saved_search_id, [[], [], None])[1]

    # Get sorting from the request. If there is no sorting option in
    # the request then use the saved sorting options.
    field = request.GET.get('sort_field', field)
    order = request.GET.get('sort_order', order)

    # Save current sorting in the session
    if 'reset' in request.params:
        request.session['%s.list.sort_field' % name] = default_field
        request.session['%s.list.sort_order' % name] = default_order
    else:
        request.session['%s.list.sort_field' % name] = field
        request.session['%s.list.sort_order' % name] = order
    request.session.save()

    return field, order


def get_search(clazz, request):
    """Returns a list of tuples with the search word and the fieldname.
    The function will first look if there is already a saved search in
    the session for the overview of the given clazz. If there is no
    previous search the start with an empty search stack.  The following
    behavior differs depending if it is a POST or GET request:

    1. GET
    Return either an empty search stack or return the saved stack in the
    session.

    2. POST
    Get the new submitted search. If the search is not already on the
    stack, then push it.  If the search word is empty, then pop the last
    search from the stack.  Finally return the modified stack.

    Please note the this function will not save the modified search
    stack in the session! This should be done elsewhere. E.g Depending
    if the search was successfull.
    """
    name = clazz.__tablename__
    # Check if there is already a saved search in the session
    saved_search = request.session.get('%s.list.search' % name, [])

    regexpr = request.session.get('%s.list.search.regexpr' % name, False)
    if "enableregexpr" in request.params:
        request.session['%s.list.search.regexpr' % name] = True
        return saved_search
    elif "disableregexpr" in request.params:
        request.session['%s.list.search.regexpr' % name] = False
        return saved_search

    if 'reset' in request.params:
        return []

    # If the request is not a equest from the search form then
    # abort here and return the saved search params if there are any.
    form_name = request.params.get('form')
    if form_name != "search":
        return saved_search

    saved_search_id = request.params.get('saved')
    if saved_search_id:
        searches_dic = request.user.settings.get('searches', {})
        if searches_dic:
            searches_dic_search = searches_dic.get(name)
            if searches_dic_search:
                return searches_dic_search.get(saved_search_id, [[],
                                               [], None])[0]
    elif "save" in request.params:
        return saved_search
    elif "delete" in request.params:
        return saved_search
    else:
        search = request.params.get('search')
        search_field = request.params.get('field')

    # If search is empty try to pop the last filter in the saved search
    if search == "" and len(saved_search) > 0:
        popped = saved_search.pop()
        log.debug('Popping %s from search stack' % repr(popped))

    # Iterate over the saved search. If the search is not already in the
    # stack push it.
    if search != "":
        found = False
        for x in saved_search:
            if search == x[0] and search_field == x[1]:
                found = True
                break
        if not found:
            log.debug('Adding search for "%s" in field "%s"' % (search,
                                                                search_field))
            saved_search.append((search, search_field, regexpr))
    return saved_search


def bundle_(request):
    clazz = request.context.__model__
    handle_history(request)
    handle_params(clazz, request)

    # Handle bundle params. If the request has the bundle_action param
    # the request is the intial request for a bundled action. In this
    # case we can delete all previous selected and stored item ids in
    # the session.
    params = request.params.mixed()
    if params.get('bundle_action'):
        request.session['%s.bundle.action' % clazz] = params.get('bundle_action')
        try:
            del request.session['%s.bundle.items' % clazz]
        except KeyError:
            pass
        request.session['%s.bundle.items' % clazz] = params.get('id', [])
    bundle_action = request.session.get('%s.bundle.action' % clazz)
    ids = request.session.get('%s.bundle.items' % clazz)
    # If the user only selects one single item it is not a list. So
    # convert it to a list with one item.
    if not isinstance(ids, list):
        ids = [ids]

    factory = clazz.get_item_factory()
    items = []
    for id in ids:
        # Check if the user is allowed to call the requested action on
        # the loaded item. If so append it the the bundle, if not ignore
        # it.
        item = factory.load(id)
        if has_permission(bundle_action.lower(), item, request):
            items.append(item)

    if bundle_action == 'Export':
        rvalue = _handle_export_request(clazz, request, items)
    elif bundle_action == 'Delete':
        rvalue = _handle_delete_request(clazz, request, items)
    return rvalue


def list__(request):
    """Wrapper method to match default signature of a view method. Will
    add the missing clazz attribut and call the wrapped method with the
    correct parameters."""
    clazz = request.context.__model__
    return list_(clazz, request)


def list_(clazz, request):
    # Important! Prevent any write access on the database for this
    # request. This is needed as transform would modify the items values
    # else.
    handle_history(request)

    # If the user enters the overview page of an item we assume that the
    # user actually leaves any context where a former set backurl is
    # relevant anymore. So delete it.
    backurl = request.session.get('%s.backurl' % clazz)
    if backurl:
        # Redirect to the configured backurl.
        del request.session['%s.backurl' % clazz]
        request.session.save()

    rvalue = {}
    search = get_search(clazz, request)
    sorting = handle_sorting(clazz, request)
    listing = clazz.get_item_list(request, user=request.user)
    listing.sort(sorting[0], sorting[1])
    listing.filter(search)
    # Only save the search if there are items
    if len(listing.items) > 0:
        request.session['%s.list.search' % clazz.__tablename__] = search
        if (request.params.get('form') == "search"):
            if "save" in request.params:
                query_name = request.params.get('save')
                user = BaseFactory(User).load(request.user.id)
                searches_dic = user.settings.get('searches', {})
                searches_dic_search = searches_dic.get(clazz.__tablename__, {})

                # Check if there is already a search saved with the name
                found = False
                for xxx in searches_dic_search.values():
                    if xxx[1] == query_name:
                        found = True
                        break
                if not found:
                    searches_dic_search[str(uuid.uuid1())] = (search, sorting, query_name)
                searches_dic[clazz.__tablename__] = searches_dic_search
                user.settings.set('searches', searches_dic)
                request.db.flush()
            elif "delete" in request.params:
                query_key = request.params.get('delete')
                user = BaseFactory(User).load(request.user.id)
                searches_dic = user.settings.get('searches', {})
                searches_dic_search = searches_dic.get(clazz.__tablename__, {})
                try:
                    del searches_dic_search[query_key]
                except:
                    pass
                searches_dic[clazz.__tablename__] = searches_dic_search
                user.settings.set('searches', searches_dic)
                request.db.flush()
        request.session.save()

    renderer = ListRenderer(listing)
    rendered_page = renderer.render(request)
    rvalue['clazz'] = clazz
    rvalue['listing'] = rendered_page
    rvalue['itemlist'] = listing
    return rvalue
