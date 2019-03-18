from time import perf_counter

import ujson as json
import hupper
import minicli
from bson import ObjectId
from jinja2 import Environment, PackageLoader, select_autoescape
from roll import Roll, Response
from roll.extensions import cors, options, traceback, simple_server

from .models import Delivery, Order, Person, Product, ProductOrder


class Response(Response):
    def html(self, template_name, *args, **kwargs):
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        context = app.context()
        context.update(kwargs)
        context["request"] = self.request
        if self.request.cookies.get("message"):
            context["message"] = json.loads(self.request.cookies["message"])
            self.cookies.set("message", "")
        self.body = env.get_template(template_name).render(*args, **context)


class Roll(Roll):
    Response = Response

    _context_func = []

    def context(self):
        context = {}
        for func in self._context_func:
            context.update(func())
        return context

    def register_context(self, func):
        self._context_func.append(func)


env = Environment(
    loader=PackageLoader("kaba", "templates"), autoescape=select_autoescape(["kaba"])
)


app = Roll()
cors(app, methods="*", headers="*")
options(app)


@app.listen("request")
async def attach_request(request, response):
    response.request = request


@app.listen("startup")
async def on_startup():
    connect()


@app.route("/", methods=["GET"])
async def home(request, response):
    response.html("home.html", deliveries=Delivery.all())


@app.route("/livraison/new", methods=["GET"])
async def new_delivery(request, response):
    response.html("edit_delivery.html", delivery={})


@app.route("/livraison/new", methods=["POST"])
async def create_delivery(request, response):
    form = request.form
    data = {}
    for name, field in Delivery.__dataclass_fields__.items():
        if name in form:
            data[name] = form.get(name)
    delivery = Delivery(**data)
    delivery.persist()
    response.status = 302
    response.headers["Location"] = f"/livraison/{delivery.id}"


@app.route("/livraison/{id}/edit", methods=["GET"])
async def edit_delivery(request, response, id):
    delivery = Delivery.load(id)
    response.html("edit_delivery.html", {"delivery": delivery})


@app.route("/livraison/{id}/edit", methods=["POST"])
async def post_delivery(request, response, id):
    delivery = Delivery.load(id)
    form = request.form
    for name, field in Delivery.__dataclass_fields__.items():
        if name in form:
            setattr(delivery, name, form.get(name))
    delivery.persist()
    response.status = 302
    response.headers["Location"] = f"/livraison/{delivery.id}"


@app.route("/livraison/{id}", methods=["GET"])
async def view_delivery(request, response, id):
    delivery = Delivery.load(id)
    total = round(sum(o.total(delivery.products) for o in delivery.orders.values()), 2)
    response.html("delivery.html", {"delivery": delivery, "total": total})


@app.route("/livraison/{id}/commander", methods=["GET"])
async def order_form(request, response, id):
    delivery = Delivery.load(id)
    email = request.query.get("email")
    order = delivery.orders.get(email)
    response.html(
        "place_order.html", {"delivery": delivery, "person": email, "order": order}
    )


@app.route("/livraison/{id}/commander", methods=["POST"])
async def place_order(request, response, id):
    delivery = Delivery.load(id)
    email = request.query.get("email")
    order = Order()
    form = request.form
    for product in delivery.products:
        quantity = form.int(product.ref, 0)
        if quantity:
            order.products[product.ref] = ProductOrder(wanted=quantity)
    if not delivery.orders:
        delivery.orders = {}
    delivery.orders[email] = order
    delivery.persist()
    response.headers["Location"] = request.url.decode()
    response.status = 302


def connect():
    # db = os.environ.get("KABA_DB", "mongodb://localhost/kaba")
    # client = MongoClient(db)
    # db = client.get_database()
    # Person.bind(db)
    # Delivery.bind(db)
    # return client
    pass


@minicli.cli()
def shell():
    """Run an ipython already connected to Mongo."""
    try:
        from IPython import start_ipython
    except ImportError:
        print('IPython is not installed. Type "pip install ipython"')
    else:
        start_ipython(
            argv=[],
            user_ns={
                "app": app,
                "Product": Product,
                "Person": Person,
                "Order": Order,
                "Delivery": Delivery,
            },
        )


@minicli.wrap
def cli_wrapper():
    connect()
    start = perf_counter()
    yield
    elapsed = perf_counter() - start
    print(f"Done in {elapsed:.5f} seconds.")


@minicli.cli
def serve(reload=False):
    """Run a web server (for development only)."""
    if reload:
        hupper.start_reloader("kaba.serve")
    traceback(app)
    simple_server(app, port=2244)


def main():
    minicli.run()
