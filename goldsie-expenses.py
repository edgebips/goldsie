#!/usr/bin/env python3
"""GLD Shareholder’s Investment Expenses Calculator.
"""
__author__ = "Martin Blais <blais@furius.ca>"
__copyright__ = "Apache License V2"

from decimal import Decimal
from os import path
from typing import Optional
import argparse
import datetime as dt
import decimal
import logging

import dateutil.parser
import petl
from petl import Record, Table

petl.config.look_style = "minimal"
petl.config.failonerror = True

ZERO = Decimal(0)
Q = Decimal("0.01")


def to_decimal(s: str) -> Decimal:
    try:
        return Decimal(s)
    except decimal.DecimalException:
        print(repr(s))
        raise


def read_transactions(filename: str, split: Optional[Decimal]) -> Table:
    """Read input file of user-provided transactions."""
    table = petl.fromcsv(filename)
    fieldnames = table.fieldnames()
    if set(fieldnames) < {"date", "instruction", "quantity"}:
        raise ValueError(f"Missing columns input: {fieldnames}")

    table = (
        table.convert("date", lambda ds: dateutil.parser.parse(ds).date())
        .convert("quantity", Decimal)
        .convert("price", Decimal)
        .sort("date")
    )
    if isinstance(split, Decimal):
        table = table.convert("quantity", lambda quantity: quantity * split).convert(
            "price", lambda price: price / split
        )
    return table


def read_gross_proceeds(tax_year: int, symbol: str) -> Table:
    """Read reference file of proceeds from the PDF document provided by SPDR."""
    filename = path.join(
        path.dirname(__file__), f"gross_proceeds/{tax_year}/gross-proceeds-{symbol}.csv"
    )
    table = (
        petl.fromcsv(filename)
        .convert("date", lambda ds: dateutil.parser.parse(ds).date())
        .convert(
            [
                "ounces_per_share",
                "per_share_ounces_sold_to_cover_expenses",
                "proceeds_per_share",
            ],
            lambda x: Decimal(x) if x else None,
        )
        .sort("date")
    )
    return table


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument("symbol", help="Name of supported symbol, e.g. GLD")
    parser.add_argument("transactions", help="Transactions CSV filename")
    parser.add_argument(
        "-s",
        "--split",
        type=to_decimal,
        action="store",
        help="Make split adjustment for quantity and price.",
    )
    default_tax_year = dt.date.today().year
    parser.add_argument(
        "-y",
        "--tax-year",
        help=f"Tax year (default: {default_tax_year})",
        default=default_tax_year,
    )
    args = parser.parse_args()

    transactions = read_transactions(args.transactions, args.split)
    reference = read_gross_proceeds(args.tax_year, args.symbol)

    def signed_quantity(prv, cur, _):
        qty = prv.signed_quantity if prv is not None else Decimal(0)
        if cur.quantity:
            sign = +1 if cur.instruction == "BUY" else -1
            qty += sign * cur.quantity
        return qty

    def basis(prv, cur, _):
        basis = prv.basis if prv is not None else Decimal(0)
        if cur.quantity:
            sign = +1 if cur.instruction == "BUY" else -1
            basis += sign * cur.quantity * cur.price
        return basis

    def oz(rec):
        return rec.signed_quantity * (rec.ounces_per_share or ZERO)

    def oz_sold(rec):
        if rec.per_share_ounces_sold_to_cover_expenses:
            return rec.signed_quantity * rec.per_share_ounces_sold_to_cover_expenses
        return Decimal(0)

    def cost_sold(rec):
        if rec.per_share_ounces_sold_to_cover_expenses and rec.oz > Decimal(0):
            cost = rec.oz_sold / rec.oz * rec.basis
        else:
            cost = Decimal(0)
        return cost.quantize(Q)

    def expenses(rec):
        if rec.proceeds_per_share:
            return (rec.signed_quantity * rec.proceeds_per_share).quantize(Q)

    table = (
        petl.outerjoin(transactions, reference, key="date")
        .select(
            lambda r: r.instruction is not None
            or r.per_share_ounces_sold_to_cover_expenses is not None
        )
        # Compute the signed quantity (buy > 0, sell < 00.
        .addfieldusingcontext("signed_quantity", signed_quantity)
        # Compute the running basis of the position at the given date.
        .addfieldusingcontext("basis", basis)
        # Compute total number of oz of the position.
        .addfield("oz", oz)
        # Compute the number of oz sold for expenses.
        .addfield("oz_sold", oz_sold)
        # Compute the cost of those oz sold for the given basis of the position.
        .addfield("cost_sold", cost_sold)
        # Compute position expense.
        .addfield("expense", expenses)
        # Filter out reference rows.
        .select(lambda r: r.expense or r.cost_sold)
        # Clean up empty columns.
        .cutout("instruction", "quantity", "price")
        # Make sure we add the position this is for.
        .addfield("symbol", args.symbol, index=0)
    )
    petl.tocsv(table, petl.StdoutSource())


if __name__ == "__main__":
    main()
