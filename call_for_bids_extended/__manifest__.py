# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)
#
#################################################################################

{
    'name': 'Call For Bids Extended',
    'version': '1.0',
    'category': 'purchase',
    'description': """
This module allows to extend two process.
=============================================
Tender Merge By,
----------------------------
* Product Suppliers,
* Product Category,
* Manually (It will merge all selected bids lines)

Best Supplier Selection Process On Tender,
----------------------------------------------------
* Create Bids,
* Generate Quotes For Multiple Suppliers,
* Send Quotes To Suppliers(via email),
* Supplier Edit Own Quote's,
* Finalize quote 
* Compare All Lines,
* Confirm Quote Lines,
* Generate Final Purchase Order.

     """,
    'author': 'TidyWay',
    'website': 'http://www.tidyway.in',
    'depends': ['purchase_requisition'],
    'data': [
             'wizard/bid_line_qty_view.xml',
             'wizard/merge_bids_view.xml',
             'wizard/generate_purchase_view.xml',
             'view/purchase_view.xml',
             ],
    'installable': True,
    'auto_install': False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
