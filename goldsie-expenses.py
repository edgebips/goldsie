#!/usr/bin/env python3
"""GLD Shareholder’s Investment Expenses Calculator.
"""
__author__ = "Martin Blais <blais@furius.ca>"
__copyright__ = "Apache License V2"

import decimal
import argparse
import logging
from decimal import Decimal
from os import path
from typing import Optional

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


def read_gross_proceeds(symbol: str) -> Table:
    """Read reference file of proceeds from the PDF document provided by SPDR."""
    filename = path.join(
        path.dirname(__file__), f"gross_proceeds/gross-proceeds-{symbol}.csv"
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
    args = parser.parse_args()

    transactions = read_transactions(args.transactions, args.split)
    reference = read_gross_proceeds(args.symbol)

    def cquantity(prv, cur, _):
        qty = prv.cquantity if prv is not None else Decimal(0)
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
        return rec.cquantity * (rec.ounces_per_share or ZERO)

    def oz_sold(rec):
        if rec.per_share_ounces_sold_to_cover_expenses:
            return rec.cquantity * rec.per_share_ounces_sold_to_cover_expenses
        return Decimal(0)

    def cost_sold(rec):
        if rec.per_share_ounces_sold_to_cover_expenses and rec.oz > Decimal(0):
            cost = rec.oz_sold / rec.oz * rec.basis
        else:
            cost = Decimal(0)
        return cost.quantize(Q)

    def expenses(rec):
        if rec.proceeds_per_share:
            return (rec.cquantity * rec.proceeds_per_share).quantize(Q)

    table = (
        petl.outerjoin(transactions, reference, key="date")
        .select(
            lambda r: r.instruction is not None
            or r.per_share_ounces_sold_to_cover_expenses is not None
        )
        .addfieldusingcontext("cquantity", cquantity)
        .addfieldusingcontext("basis", basis)
        .addfield("oz", oz)
        .addfield("oz_sold", oz_sold)
        .addfield("cost_sold", cost_sold)
        .addfield("expense", expenses)
        .select(lambda r: r.expense or r.cost_sold)
        .cutout("cost", "instruction", "quantity", "price")
        .addfield("symbol", args.symbol, index=0)
    )
    petl.tocsv(table, petl.StdoutSource())


if __name__ == "__main__":
    main()
