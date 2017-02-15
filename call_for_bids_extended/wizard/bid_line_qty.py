# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)
#
#################################################################################

from odoo import fields, models, api, _
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp

class BidLineQty(models.Model):
    _name = "bid.line.qty"
    _description = "Change Bid line quantity"
    qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)

    @api.multi
    def change_qty(self):
        active_ids = self._context and self._context.get('active_ids', [])
        purchase_lines = self.env['purchase.order.line'].browse(active_ids)
        for line in purchase_lines:
            if self.qty > line.product_qty:
                raise Warning(_(""" you cannot put more then ordered qty."""))
            line.write({'quantity_bid': self.qty})
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
