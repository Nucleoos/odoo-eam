# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)
#
#################################################################################

{
    'name': 'MRO Labor Task Management',
    'version': '2.0',
    'category': 'mrp',
    'summary': 'Labor Task Management',
    'description': """
Module will allow to put Labor timesheet on MRO Order.
===============================================================
* Manage a labor task
    * Work summary
    * Done By,
    * Initial Time(HH:MM:SS)
    * End Time(HH:MM:SS)
    * Duration(HH:MM:SS)
* Maintenance Order
    * Auto generate analytic accounts for all orders,
    * Also updated old orders with analytic accounts,
    * Total Hours spent by Labors.

     """,
    'author': 'TidyWay',
    'website': 'http://www.tidyway.in',
    'depends': ['mro', 'analytic', 'hr_timesheet'],
    'data': [
             'view/mro_task_view.xml',
             ],
    'installable': True,
    'auto_install': False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
