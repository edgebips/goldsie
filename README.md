# GLD Shareholder’s Investment Expenses Calculator

If you held a position in GLD throughout the year, you have to report sales the
fund makes to cover expenses. What's more, is that you need to calculate the
cost basis yourself, and this isn't trivial.

See here for details:
https://www.spdrgoldshares.com/media/GLD/file/SPDR-Gold-Trust-Tax-Information-2021.pdf

Inspecting your 1099-B, you may seem something like this:

    UNDETERMINED TERM TRANSACTIONS FOR NONCOVERED TAX LOTS

    01/11/21 0.000 17.67 N/A ... ... ... Principal payment 16 Cost Basis Factor: 0.000340025
    02/05/21 0.000 18.10 N/A ... ... ... Principal payment 16 Cost Basis Factor: 0.000356997
    03/03/21 0.000 32.66 N/A ... ... ... Principal payment 16 Cost Basis Factor: 0.000339295
    04/07/21 0.000 33.69 N/A ... ... ... Principal payment 16 Cost Basis Factor: 0.000344745

You will note that the dates correspond to those that have expenses in the PDF above.

*This project computes the cost basis for you.*

(Note to future self: to find the gross proceeds, look on Google for e.g., `iau
silver trust 2022 gross proceeds file`. iShare provides a spreadsheet; I saved
and hand-cleaned the file. For `GLD`, I copy-pasted the PDF contents and cleaned
it up by hand. Takes 5 mins.)


# Transactions Input Format

You need to provide a table of purchases and sales in CSV format (with headers),
with at least the following columns (other columns are ignored):

 * `date`: The date at which the transaction occurred.
 * `instruction`: A `BUY` or `SELL` string, indicating your instruction.
 * `quantity`: An integer, the number of shared bought or sold.
 * `price`: A float, the price per share of the transaction.

For example:

    date,instruction,quantity,price
    1/22/2021,BUY,150,174.20
    5/05/2021,SELL,50,168.02
    7/16/2021,SELL,100,169.70


# Supported Years

This project only supports year 2021 so far. If anyone would like to extend it
and contribute other tax years, patches are welcome.

# Supported Names

 * `GLD`
 * `SLV`
 * `IAU`: Note that the numbers have been adjusted for the 5/24/2021 split.

# Disclaimer

Note that no guarantee is made of correctness. WARNING: if you use this code you
will lose all your money in a jiffy and I can't be held responsible. You've been
warned.
