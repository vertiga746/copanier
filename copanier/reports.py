from openpyxl import Workbook
from openpyxl.writer.excel import save_virtual_workbook


def summary(delivery):
    wb = Workbook()
    ws = wb.active
    ws.title = f"{delivery.producer} {delivery.from_date.date()}"
    ws.append(["ref", "produit", "prix", "unités", "total"])
    for product in delivery.products:
        wanted = delivery.product_wanted(product)
        ws.append(
            [
                product.ref,
                product.name,
                product.price,
                wanted,
                round(product.price * wanted, 2),
            ]
        )
    ws.append(["", "", "", "Total", delivery.total])
    return save_virtual_workbook(wb)


def full(delivery):
    wb = Workbook()
    ws = wb.active
    ws.title = f"{delivery.producer} {delivery.from_date.date()}"
    headers = ["ref", "produit", "prix"] + [e for e in delivery.orders] + ["total"]
    ws.append(headers)
    for product in delivery.products:
        row = [product.ref, product.name, product.price]
        for order in delivery.orders.values():
            wanted = order.products.get(product.ref)
            row.append(wanted.wanted if wanted else 0)
        row.append(delivery.product_wanted(product))
        ws.append(row)
    footer = ["Total", "", ""] + [
        o.total(delivery.products) for o in delivery.orders.values()
    ] + [delivery.total]
    ws.append(footer)
    return save_virtual_workbook(wb)