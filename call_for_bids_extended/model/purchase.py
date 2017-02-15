# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)
#
#################################################################################

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, Warning
import odoo.addons.decimal_precision as dp

class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    merged = fields.Boolean('Merged', readonly=True, copy=False)
    mprocurement_ids = fields.One2many('procurement.order', 'requisition_id', string='Linked Procurements',copy=False,readonly=True)
    merge_to_id = fields.Many2one('purchase.requisition',string='Merged To',copy=False,readonly=True)
    merge_from_ids = fields.One2many('purchase.requisition','merge_to_id',string='Merged From',readonly=True)
    origin = fields.Text('Source Document')
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'Sent to Suppliers'),
                               ('open', 'Bid Selection'), ('done', 'Done'),
                               ('cancel', 'Cancelled')],
                              'Status', track_visibility='onchange', required=True,
                              copy=False, default='draft')

#     @api.constrains('date_end', 'ordering_date', 'schedule_date')
#     def _check_closing_date(self):
#         for tender in self:
#             if tender.date_end and tender.ordering_date and tender.date_end >= tender.ordering_date:
#                 raise ValidationError(_('Ordering date cannot be set before agreement deadline.'))
#             if tender.date_end and tender.schedule_date and tender.date_end >= tender.schedule_date:
#                 raise ValidationError(_('schedule date cannot be set before agreement deadline.'))

    @api.multi
    def action_open(self):
        if not [x.id for x in self.purchase_ids if x.state not in ('cancel')]:
            raise Warning(_(""" At least one supplier should be selected."""))
        return super(PurchaseRequisition, self).action_open()

    @api.multi
    def action_in_progress(self):
        for record in self:
            if not record.purchase_ids:
                raise Warning(_('At least one supplier should be selected.'))
            self.send_quotation_to_supplier(record.purchase_ids)
        return super(PurchaseRequisition, self).action_in_progress()

    @api.model
    def send_quotation_to_supplier(self, purchase_ids):
        """
            Send email to all quote suppliers
        """
        ir_model_data = self.env['ir.model.data']
        cmp_msg_obj = self.env['mail.compose.message']
        try:
            template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
        except ValueError:
            template_id = False

        for purchase in purchase_ids:
            onchange_res = cmp_msg_obj.onchange_template_id(template_id, 'comment', 'purchase.order', purchase.id)['value']
            compose_id = cmp_msg_obj.with_context({
                                                    'default_model': 'purchase.order',
                                                    'default_res_id': purchase.id,
                                                    'default_use_template': bool(template_id),
                                                    'default_template_id': template_id,
                                                    'default_composition_mode': 'comment',
                                                    #'send_mail': True
                                                   }).create(onchange_res)
            compose_id.send_mail()
        return True

    @api.multi
    def action_get_quote(self):
        self.ensure_one()
        if not self.line_ids:
            raise Warning(_('You cannot generate quote without product line.'))
        action = self.env.ref('purchase_requisition.action_purchase_requisition_to_so').read()[0]
        action['context'] = {"default_requisition_id": self.id}
        action['domain'] = [('requisition_id','=', self.id)]
        return action

    @api.multi
    def open_bid_lines(self):
        if not self.line_ids:
            raise Warning(_('You cannot generate quote without product line.'))
        if not [x.id for x in self.purchase_ids if x.state != 'cancel']:
            raise Warning(_('At least one supplier should be selected.'))
        action = self.env.ref('call_for_bids_extended.purchase_line_tree').read()[0]
        po_lines = []
        for po in self.purchase_ids:
            po_lines += [po_line.id for po_line in po.order_line]
        action['context'] = {
            'search_default_groupby_product': True,
            'search_default_hide_cancelled': True,
            'tender_id': self.id,
        }
        action['domain'] = [('id', 'in', po_lines)]
        return action

    @api.model
    def check_valid_quotation(self, quotation):
        """
        Check if a quotation has all his order lines bid in order to confirm it if its the case
        return True if all order line have been selected during bidding process, else return False

        args : 'quotation' must be a browse record
        """
        for line in quotation.order_line:
            if line.confirmed or line.product_qty != line.quantity_bid:
                return False
        return True

    @api.multi
    def _get_purchase_lines(self):
        self.ensure_one()
        total_ids = []
        for po in self.purchase_ids:
            total_ids += [po_line for po_line in po.order_line if po_line.state != 'cancel']
        return total_ids

    @api.multi
    def _prepare_po_from_tender(self):
        """ Prepare the values to write in the purchase order
        created from a tender.

        :param tender: the source tender from which we generate a purchase order
        """
        self.ensure_one()
        return {'order_line': [],
                'requisition_id': self.id,
                'origin': self.name
                }

    @api.model
    def _prepare_po_line_from_tender(self, line, purchase_id):
        """ Prepare the values to write in the purchase order line
        created from a line of the tender.

        :param tender: the source tender from which we generate a purchase order
        :param line: the source tender's line from which we generate a line
        :param purchase_id: the id of the new purchase
        """
        return {
                'product_qty': line.quantity_bid,
                'order_id': purchase_id
                }

    @api.multi
    def cancel_unconfirmed_quotations(self):
        self.ensure_one()
        #cancel other orders
        for quotation in self.purchase_ids:
            if quotation.state in ['draft', 'sent', 'bid']:
                quotation.button_cancel()
                quotation.message_post(body=_('Cancelled by the call for bids associated to this request for quotation.'))
        return True

    @api.multi
    def generate_po(self):
        """
        Generate all purchase order based on selected lines, should only be called on one tender at a time
        """
        self.ensure_one()
        po_obj = self.env['purchase.order']
        poline_obj = self.env['purchase.order.line']
        id_per_supplier = {}
        for tender in self:
            all_purchase_lines = tender._get_purchase_lines()
            if tender.state == 'done':
                raise Warning(_('You have already generate the purchase order(s).'))

            confirm = False
            #check that we have at least confirm one line
            for po_line in all_purchase_lines:
                if po_line.confirmed:
                    confirm = True
                    break
            if not confirm:
                raise Warning(_('You have no line selected for buying.'))

            #check for complete RFQ
            for quotation in tender.purchase_ids:
                if (self.check_valid_quotation(quotation)):
                    quotation.button_confirm()

            #get other confirmed lines per supplier
            for po_line in all_purchase_lines:
                #only take into account confirmed line that does not belong to already confirmed purchase order
                if po_line.confirmed and po_line.order_id.state in ['draft', 'sent', 'bid']:
                    if id_per_supplier.get(po_line.partner_id.id):
                        id_per_supplier[po_line.partner_id.id].append(po_line)
                    else:
                        id_per_supplier[po_line.partner_id.id] = [po_line]

            #generate po based on supplier and cancel all previous RFQ
            for supplier, product_line in id_per_supplier.items():
                #copy a quotation for this supplier and change order_line then validate it
                quotation_id = po_obj.search([('requisition_id', '=', tender.id), ('partner_id', '=', supplier)], limit=1)[0]
                vals = tender._prepare_po_from_tender()
                new_po = quotation_id.copy(default=vals)
                #duplicate po_line and change product_qty if needed and associate them to newly created PO
                for line in product_line:
                    vals = self._prepare_po_line_from_tender(line, new_po.id)
                    line.copy(default=vals)
                #use workflow to set new PO state to confirm
                new_po.button_confirm()

            #cancel other orders
            tender.cancel_unconfirmed_quotations()

            #set tender to state done
            tender.action_done()

        action = self.env.ref('purchase_requisition.action_purchase_requisition').read()[0]
        action['domain'] = [('id','in', [self.id])]
        return action

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('quantity_bid', 'price_unit','confirmed')
    def bid_subtotal_value(self):
        for rec in self:
            rec.bid_subtotal = rec.quantity_bid * rec.price_unit

    quantity_bid = fields.Float('Quantity Bid', digits=dp.get_precision('Product Unit of Measure'), help="Technical field for not loosing the initial information about the quantity proposed in the bid")
    confirmed = fields.Boolean(string="Confirm?")
    bid_subtotal = fields.Monetary(compute='bid_subtotal_value', string='To Subtotal', store=True)

    @api.multi
    def action_confirm_line(self):
        for element in self:
            to_do = {'confirmed': True}
            if not element.quantity_bid:
                to_do.update({
                              'quantity_bid': element.product_qty,
                              })
            element.write(to_do)
        return True

    @api.multi
    def action_draft_line(self):
        for element in self:
            element.write({'quantity_bid': 0.0, 'confirmed': False})
        return True


#     def cancel_all_procurements(self, cr, uid, context=None):
#         """
#         Process
#             -cancel all procurements related to cancel bids
#         """
#         proc_obj = self.pool.get('procurement.order')
#         pick_obj = self.pool.get('stock.picking')
#         allcancel_bids = self.search(cr, 1, [('state','=','cancel')])
# 
#         #SECOND PROCESS
#         need_to_cancel,need_to_done = [],[]
#         all_running_procurs = proc_obj.search(cr, 1, [('state','=','running')])
#         for proc in proc_obj.browse(cr, 1, all_running_procurs):
# #             #1)if procurement requisition is on cancel then procurement should be on cancel state
#             if proc.requisition_id and proc.requisition_id.state == 'cancel':
#                 need_to_cancel.append(proc.id)
#             #2)Sale Order(MTO) Already delivered then procurement should be in done state
#             if proc.move_dest_id:
#                 if proc.group_id:
#                     all_picks = pick_obj.search(cr, 1, [('group_id', '=', proc.group_id.id),('picking_type_code','=','outgoing'),('state','=','done')], context=context)
#                     if all_picks:
#                         cr.execute("SELECT sum(product_uom_qty) FROM stock_move WHERE picking_id IN %s  AND product_id = %s ", (tuple(all_picks), proc.product_id.id,))
#                         transfered_qty = cr.fetchone()[0] or 0.0
#                         if transfered_qty >= proc.product_qty:
#                             need_to_done.append(proc.id)
#             else:
#                 #3)Purchase oder => received with same qty then procurement should be done
#                 if proc.requisition_id:
#                     purchase_ids = proc.requisition_id.purchase_ids
#                     picking_ids = []
#                     for purchase in purchase_ids:
#                         if purchase.state != 'cancel':
#                             picking_ids += [picking.id for picking in purchase.picking_ids]
#                     if picking_ids:
#                         cr.execute("SELECT sum(product_uom_qty) FROM stock_move WHERE picking_id IN %s  AND product_id = %s AND state = 'done'", (tuple(picking_ids), proc.product_id.id,))
#                         recieved_qty = cr.fetchone()[0] or 0.0
#                         if recieved_qty >= proc.product_qty:
#                             need_to_done.append(proc.id)
# 
#         need_to_cancel = list(set(need_to_cancel))
#         need_to_done = list(set(need_to_done))
# 
#         if need_to_cancel:
#                 try:
#                     proc_obj.cancel(cr, 1, need_to_cancel)
#                 except: pass
#         if need_to_done:
#                 try:
#                     proc_obj.write(cr, 1, need_to_done, {'state':'done'})
#                 except: pass
# 
#         return True
# 
# class purchase_order(models.Model):
#     _inherit = "purchase.order"
# 
#     def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
#         stock_move_lines = super(purchase_order, self)._prepare_order_line_move(cr, uid, order, order_line, picking_id, group_id, context=context)
# 
#         #For Regular tenders
#         if order.requisition_id and (not order.requisition_id.merged) and order.requisition_id.procurement_id and order.requisition_id.procurement_id.move_dest_id:
#             for i in range(0, len(stock_move_lines)):
#                 stock_move_lines[i]['move_dest_id'] = order.requisition_id.procurement_id.move_dest_id.id
# 
#         #For Merged tenders#compare with all procurements which are merged!!
#         if order.requisition_id and order.requisition_id.merged and order.requisition_id.mprocurement_ids:
#             all_procurements = order.requisition_id.mprocurement_ids
#             for i in range(0, len(stock_move_lines)):
#                 for proc in all_procurements:
#                     if stock_move_lines[i]['product_id'] == proc.product_id.id and proc.move_dest_id:
#                         stock_move_lines[i]['move_dest_id'] = proc.move_dest_id.id
# 
#         return stock_move_lines
# 
# 
# class procurement_order(models.Model):
#     _inherit = 'procurement.order'
# 
#     def _check(self, cr, uid, procurement, context=None):
#         if procurement.rule_id and procurement.rule_id.action == 'buy' and procurement.product_id.purchase_requisition:
#             if procurement.requisition_id.state in ('in_progress','open','done'):
#                 if any([purchase.shipped for purchase in procurement.requisition_id.purchase_ids]):
#                     return True
#             return False
#         return super(procurement_order, self)._check(cr, uid, procurement, context=context)
