from pyramid.view import view_config


@view_config(route_name='view_wiki')
def view_wiki(request):
    "Redirect to the FrontPage wiki page."

@view_config(route_name='view_page', renderer='templates/view.pt')
def view_page(request):
    "View a single wiki page."

@view_config(route_name='add_page', renderer='templates/edit.pt')
def add_page(request):
    "Add a new wiki page."

@view_config(
    route_name='edit_page', renderer='templates/edit.pt',
    request_method=("GET", "POST"))
def edit_page(request):
    "Edit an existing wiki page."
