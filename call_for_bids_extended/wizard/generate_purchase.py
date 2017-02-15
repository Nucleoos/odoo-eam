# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)
#
#################################################################################

from odoo import models, api, _
from odoo.exceptions import Warning

class GeneratePo(models.TransientModel):

    """ To create Purchase for purchase order line"""

    _name = 'generate.po'
    _description = 'Generate Purchase Order'

    @api.multi
    def generate_po(self):
        """
            Create Purchase order from selected bid lines
        """
        self.ensure_one()
        all_purchase_lines = self._context.get('active_ids', []) or []
        all_po_lines = self.env['purchase.order.line'].browse(all_purchase_lines)
        tender_ids = []
        tender_states = []
        for line in all_po_lines:
            if line.order_id and line.order_id.requisition_id:
                tender_ids.append(line.order_id.requisition_id.id)
                tender_states.append(line.order_id.requisition_id.state)
        tender_ids = list(set(tender_ids))
        tender_states = list(set(tender_states))
        if not tender_ids:
            raise Warning(_('you are only generate purchase order for tender.'))
        if len(tender_ids) > 1:
            raise Warning(_('Selected lines must be from same tender.'))
        if len(tender_states) > 1:
            raise Warning(_('All Selected lines tender must be on "BID SELECTION" State.'))
        if 'open' not in tender_states:
            raise Warning(_('Selected lines Tender must be on "BID SELECTION" State.'))

        tender_rec = self.env['purchase.requisition'].browse(tender_ids)
        return tender_rec.generate_po()