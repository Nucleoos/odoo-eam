# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)
#
#################################################################################

from odoo import fields, models, api, _
from odoo.exceptions import Warning

class merge_bids_lines(models.TransientModel):
    _name = "merge.bids.lines"

    requisition_id = fields.Many2one('purchase.requisition', string='Requisition', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    supplier_id = fields.Many2one('res.partner', string='Product Supplier', readonly=True)
    merge_id = fields.Many2one('merge.bids', string='Merge ID')

class merge_bids(models.TransientModel):
    _name = "merge.bids"
    _description = "Call For Bids Merge"

    @api.model
    def default_get(self, fields):
        """ 
        To get default values for the object.
        """
        tender_ids = self._context.get('active_ids',[]) or []
        prod_obj = self.env['product.product']
        res = {}
        if 'tender_line_ids' in fields:
            self._cr.execute(""" 
                                SELECT prl.product_id,pr.id as requisition_id 
                                FROM purchase_requisition_line prl, purchase_requisition pr
                                WHERE prl.requisition_id = pr.id AND prl.product_id IS NOT NULL AND pr.id in %s""", 
                            (tuple(tender_ids),))

            data = self._cr.dictfetchall()
            for l in data:
                product = prod_obj.browse(l['product_id'])
                total_sellers = product.seller_ids and [x.name.id for x in product.seller_ids]
                supplier_id = total_sellers and total_sellers[0] or False
                l.update({
                          'categ_id': product and product.categ_id and product.categ_id.id or False,
                          'supplier_id': supplier_id
                          })
            final_list = [(0, 0, p) for p in data]
            res['tender_line_ids'] = final_list
        return res

    base_on = fields.Selection([('category', 'Category'), ('supplier', 'Product Supplier'), ('manually', 'Manually')], string='Base On', required=True)
    tender_line_ids = fields.One2many('merge.bids.lines','merge_id',string='Tender Lines')
    category_ids = fields.Many2many('product.category', string='Select Categories')
    supplier_ids = fields.Many2many('res.partner', string='Select Suppliers', domain=[('supplier', '=', True)])

    @api.onchange('base_on', 'tender_line_ids')
    def onchange_base_on(self):
        res = {'domain': {}}
        category_ids,supplier_ids = [],[]
        for line in self.tender_line_ids:
            line.categ_id and category_ids.append(line.categ_id.id)
            line.supplier_id and supplier_ids.append(line.supplier_id.id)
        if category_ids:
            res['domain']['category_ids'] = [('id','in',category_ids)]
        if supplier_ids:
            res['domain']['supplier_ids'] = [('id','in',supplier_ids)]
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        -Process
            -Check in initial condition about minumun 2 orders to be needed to merge.
            -All are in draft state.
        """
        bid_obj = self.env['purchase.requisition']
        ctx = dict(self._context)
        record_ids = ctx and ctx.get('active_ids', []) or []
        res = super(merge_bids, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if not record_ids:
            return res
         
        if ctx.get('active_model', '') == 'purchase.requisition' and len(ctx['active_ids']) < 2:
            raise Warning(_('Please select multiple bids to merge in the list view.'))

        bid_recors = bid_obj.browse(record_ids)
        all_states = [x.state for x in bid_recors]
        if not (all_states and all_states[1:] == all_states[:-1] and ('draft' in all_states)):
            raise Warning(_('Only Draft bids can be merged, please select only draft bids.'))

        #company
        company_ids, warehouse_ids, picking_type_ids = [], [], []
        for alldata in bid_recors:
            alldata.company_id and company_ids.append(alldata.company_id.id)
            alldata.warehouse_id and warehouse_ids.append(alldata.warehouse_id.id)
            alldata.picking_type_id and picking_type_ids.append(alldata.picking_type_id.id)
        if not (company_ids[1:] == company_ids[:-1]):
            raise Warning(_('Companies must be same to merge bids(Tenders).'))
        if not (warehouse_ids[1:] == warehouse_ids[:-1]):
            raise Warning(_('Warehouses must be same to merge bids(Tenders).'))
        if not (picking_type_ids[1:] == picking_type_ids[:-1]):
            raise Warning(_('Picking Type must be same to merge bids(Tenders).'))
        return res

    @api.model
    def apply_common(self, tender_ids, new_tender_id):
        """
        If not select any category or manufacturer,then apply it as common new tender with all lines.
        """
        req_obj = self.env['purchase.requisition']
        req_line_obj = self.env['purchase.requisition.line']
        proc_obj = self.env['procurement.order']
        total_line_ids, procure_ids, need_to_cancel = [], [], []
        for all in req_obj.browse(tender_ids):
            need_to_cancel.append(all.id)
            total_line_ids.extend([x.id for x in all.line_ids])
            all_attached_procures = proc_obj.search([('requisition_id', '=', all.id)])
            all_attached_procures and procure_ids.extend([x.id for x in all_attached_procures])
        for copy_line in total_line_ids:
            crline = req_line_obj.browse(copy_line)
            crline.copy(default={'requisition_id': new_tender_id})
        procure_ids = list(set(procure_ids))
        if procure_ids:
            procure_records = proc_obj.browse(procure_ids)
            procure_records.write({'requisition_id': new_tender_id})
        need_to_cancel = list(set(need_to_cancel))
        all_need_to_cancel = req_obj.browse(need_to_cancel)
        all_need_to_cancel.action_cancel()
        #add merged id to cancel tenders
        need_to_cancel and all_need_to_cancel.write({'merge_to_id': new_tender_id})
        if need_to_cancel:
            total_req_usaged = list(set(need_to_cancel))
            all_canclled_r =' '.join([str(x.name) for x in req_obj.browse(total_req_usaged)])
            N_Tender = req_obj.browse(new_tender_id)
            N_Tender.write({
                          'origin': all_canclled_r,
                          'merged':True, 
                          })
        return True

    @api.model
    def _find_tender_dual(self, all_tender_ids):
        """
        Find which tender have multiple lines.
        """
        req_obj = self.env['purchase.requisition']
        single, dual = [], []
        for rec in req_obj.browse(all_tender_ids):
            if len(rec.line_ids) > 1:
                dual.append(rec.id)
            else:
                single.append(rec.id)
        return single, dual
  
    @api.model
    def _process_by_category(self, category_ids, all_tender_ids, new_tender_id):
        req_obj = self.env['purchase.requisition']
        proc_obj = self.env['procurement.order']
        need_to_cancel, delete_ids,procure_ids = [], [],[]
        create_copy = False
        single_line, dual_lines = self._find_tender_dual(all_tender_ids)
  
        # Single Line process#cancel all tenders
        if single_line:
            for rec in req_obj.browse(single_line):
                line_rec = rec.line_ids[0]
                if line_rec.product_id and (line_rec.product_id.categ_id.id in category_ids):
                    need_to_cancel.append(rec.id)
                    all_attached_procures = proc_obj.search([('requisition_id', '=', rec.id)])
                    all_attached_procures and procure_ids.extend([a.id for a in all_attached_procures])
                    create_copy = True
                    line_rec.copy(default={'requisition_id': new_tender_id})
                    #Update Procurement!!#update at the end
                    #all_attached_procures and proc_obj.write(cr, uid, all_attached_procures, {'requisition_id': new_tender_id})
  
        # Dual Line process#Delete all lines
        if dual_lines:
            for rec in req_obj.browse(dual_lines):
                all_cate_ids = [x.product_id and x.product_id.categ_id.id for x in rec.line_ids]
                all_cate_ids = filter(None, all_cate_ids)
                #if list(set(all_cate_ids)) == category_ids:
                if set(all_cate_ids).issubset(set(category_ids)):
                    for line in rec.line_ids:
                        create_copy = True
                        need_to_cancel.append(rec.id)
                        all_attached_procures = proc_obj.search([('requisition_id', '=', rec.id)])
                        all_attached_procures and procure_ids.extend([a.id for a in all_attached_procures])
                        line.copy(default={'requisition_id': new_tender_id})
                        #Update Procurement!!#update at the end
                        #all_attached_procures and proc_obj.write(cr, uid, all_attached_procures, {'requisition_id': new_tender_id})
 
                else:
                    create_new_copy = False
                    create_new_copy_lines = []
                    for line in rec.line_ids:
                        if line.product_id and (line.product_id.categ_id.id in category_ids):
                            create_new_copy = True
                            create_copy = True
                            #delete_ids.append(rec.id)
                            need_to_cancel.append(rec.id)
                            all_attached_procures = proc_obj.search([('requisition_id', '=', rec.id)])
                            all_attached_procures and procure_ids.extend([a.id for a in all_attached_procures])
                            line.copy(default={'requisition_id': new_tender_id})
                            #self._cr.execute(""" DELETE FROM purchase_requisition_line WHERE id = %s""" % (line.id))
                        else:
                            create_new_copy_lines.append(line)
                    if create_new_copy:
                        new_rec = rec.copy(default={'origin': rec.name, 'line_ids': False})
                        for add_new in create_new_copy_lines:
                            add_new.copy(default={'requisition_id': new_rec.id})
  
        if not create_copy:
            raise Warning(_('bid Lines could not found of this categories.'))
#       #cancel all merge tenders
        need_to_cancel = list(set(need_to_cancel))
        all_need_to_cancel = req_obj.browse(need_to_cancel)
        #req_obj.tender_cancel(need_to_cancel)
        all_need_to_cancel.action_cancel()
        #merge old requisition.
        procure_ids = list(set(procure_ids))
        if procure_ids:
            proc_obj.write(procure_ids, {'requisition_id': new_tender_id})
 
        #add merged id to cancel tenders
        need_to_cancel and all_need_to_cancel.write({'merge_to_id': new_tender_id})
        #add valeus to new tender
        if need_to_cancel or delete_ids:
            total_req_usaged = list(set(need_to_cancel + delete_ids))
            all_canclled_r =' '.join([str(x.name) for x in req_obj.browse(total_req_usaged)])
            N_Tender = req_obj.browse(new_tender_id)
            N_Tender.write({
                          'origin': all_canclled_r,
                          'merged':True, 
                          })
        return True

    @api.model
    def _merge_process_by_category(self, category_ids, all_tender_ids, new_tender_id):
        """
        Category Ids
        """
        self._process_by_category(category_ids, all_tender_ids, new_tender_id)
        return True

    @api.model
    def _process_by_manufacturer(self, supplier_ids, all_tender_ids, new_tender_id):
        req_obj = self.env['purchase.requisition']
        proc_obj = self.env['procurement.order']
        need_to_cancel, delete_ids,procure_ids = [], [],[]
        create_copy = False
        single_line, dual_lines = self._find_tender_dual(all_tender_ids)
  
        # Single Line process#cancel all tenders
        if single_line:
            for rec in req_obj.browse(single_line):
                line_rec = rec.line_ids and rec.line_ids[0]
                if line_rec.product_id and (line_rec.product_id.seller_ids):
                    total_sellers = [x.name.id for x in line_rec.product_id.seller_ids]
                    supplier_id = total_sellers and total_sellers[0] or False
                    if supplier_id in supplier_ids:
                        need_to_cancel.append(rec.id)
                        all_attached_procures = proc_obj.search([('requisition_id', '=', rec.id)])
                        all_attached_procures and procure_ids.extend([y.id for y in all_attached_procures])
                        create_copy = True
                        line_rec.copy(default={'requisition_id': new_tender_id})
  
        # Dual Line process#Delete all lines
        if dual_lines:
            for rec in req_obj.browse(dual_lines):
                all_pre_manufacturer = []
                for oo in rec.line_ids:
                    if oo.product_id and oo.product_id.seller_ids:
                        total_xsellers = [x.name.id for x in oo.product_id.seller_ids]
                        supplier_xid = total_xsellers and total_xsellers[0] or False
                        if supplier_xid:
                            all_pre_manufacturer.append(supplier_xid)

                all_pre_manufacturer
                #all_manufacturer_ids = [x.product_id and x.product_id.seller_id and x.product_id.seller_id.id for x in rec.line_ids]
                all_manufacturer_ids = filter(None, all_pre_manufacturer)

                #if list(set(all_manufacturer_ids)) == manufacturer_ids:
                if set(all_manufacturer_ids).issubset(set(supplier_ids)) and (len(all_pre_manufacturer) == len(rec.line_ids)):
                    for line in rec.line_ids:
                        create_copy = True
                        need_to_cancel.append(rec.id)
                        all_attached_procures = proc_obj.search([('requisition_id', '=', rec.id)])
                        all_attached_procures and procure_ids.extend([z.id for z in all_attached_procures])
                        line.copy(default={'requisition_id': new_tender_id})
  
                else:
                    create_new_copy = False
                    create_new_copy_lines = []
                    for line in rec.line_ids:
                        if line.product_id:
                            total_sellers = line.product_id.seller_ids and [x.name.id for x in line.product_id.seller_ids]
                            supplier_yid = total_sellers and total_sellers[0] or False
                            if supplier_yid and (supplier_yid  in supplier_ids):
                                create_new_copy = True
                                create_copy = True
                                #delete_ids.append(rec.id)
                                need_to_cancel.append(rec.id)
                                all_attached_procures = proc_obj.search([('requisition_id', '=', rec.id)])
                                all_attached_procures and procure_ids.extend([o.id for o in all_attached_procures])
                                line.copy(default={'requisition_id': new_tender_id})
                                #self._cr.execute(""" DELETE FROM purchase_requisition_line WHERE id = %s""" % (line.id))
                            else:
                                create_new_copy_lines.append(line)
                        else:
                            create_new_copy_lines.append(line)
                    if create_new_copy:
                        create_new_copy_lines = list(set(create_new_copy_lines))
                        new_rec = rec.copy(default={'origin': rec.name, 'line_ids': False})
                        for add_new in create_new_copy_lines:
                            add_new.copy(default={'requisition_id': new_rec.id})
  
        if not create_copy:
            raise Warning(_('Bid Lines could not found of this suppliers.'))
  
        #merge old requisition.
        procure_ids = list(set(procure_ids))
        if procure_ids:
            x_procure_ids = proc_obj.browse(procure_ids)
            x_procure_ids.write({'requisition_id': new_tender_id})
  
#       #cancel all merge tenders
        need_to_cancel = list(set(need_to_cancel))
        all_need_to_cancel = req_obj.browse(need_to_cancel)
        all_need_to_cancel.action_cancel()
 
        #add merged id to cancel tenders
        need_to_cancel and all_need_to_cancel.write({'merge_to_id': new_tender_id})
        #add values to new tender
        if need_to_cancel or delete_ids:
            total_req_usaged = list(set(need_to_cancel + delete_ids))
            all_canclled_r =' '.join([str(x.name) for x in req_obj.browse(total_req_usaged)])
            N_Tender = req_obj.browse(new_tender_id)
            N_Tender.write({
                          'origin': all_canclled_r, 
                          'merged':True, 
                          })
        return True

    @api.model
    def _merge_process_by_manufacturer(self, supplier_ids, all_tender_ids, new_tender_id):
        """
        Supplier Ids
        """
        self._process_by_manufacturer(supplier_ids, all_tender_ids, new_tender_id)
        return True
 
    @api.model
    def _create_tender(self, all_tender_ids):
        req_obj = self.env['purchase.requisition']
        tender_rec = req_obj.browse(all_tender_ids[0])
        req_rec = req_obj.create({
                            'name': self.env['ir.sequence'].next_by_code('purchase.order.requisition') or '/',
                            'warehouse_id': tender_rec.warehouse_id.id,
                            'company_id': tender_rec.company_id.id,
                            })
        return req_rec.id

    @api.model
    def group_by_products(self, new_tender_id):
        """
        Group Entries
            Product A : 1 Qty
            Product A : 1 Qty
            Product A : 1 Qty
            Product B : 2 Qty
            Product c : 1 Qty
            Product c : 1 Qty
        Output will be
            Product A : 3 Qty
            Product B : 2 Qty
            Product c : 2 Qty
        """
        req_obj = self.env['purchase.requisition']
        req_line_obj = self.env['purchase.requisition.line']
        current = req_obj.browse(new_tender_id)
        if not current.line_ids:
            return True
        self._cr.execute(""" 
                        SELECT prl.product_id, sum(prl.product_qty/u.factor*u2.factor) as product_qty 
                        FROM purchase_requisition_line prl 
                        LEFT JOIN purchase_requisition pr ON (prl.requisition_id = pr.id)
                        LEFT JOIN product_product p on (prl.product_id =p.id)
                        LEFT JOIN product_template t on (p.product_tmpl_id=t.id)
                        LEFT JOIN product_uom u ON (u.id=prl.product_uom_id)
                        LEFT JOIN product_uom u2 ON (u2.id=t.uom_id)
                        WHERE prl.product_id IS NOT NULL AND prl.product_uom_id IS NOT NULL AND pr.id = %s 
                        GROUP BY prl.product_id
                        """, 
                    (new_tender_id,))
        values = self._cr.dictfetchall()
        #req_line_obj.unlink([x.id for x in current.line_ids])
        current.line_ids.unlink()
        for args in values:
            product = self._find_product_rec(args.get('product_id'))
            args.update({
                         'product_id': product.id,
                         'product_uom_id': product.uom_id.id,
                         'product_qty': args.get('product_qty', 0.0) or 0.0,
                         'requisition_id': new_tender_id
                         })
            req_line_obj.create(args)
        return True
 
    @api.model
    def _find_product_rec(self, product_id):
        return self.env['product.product'].browse(product_id)
 
    @api.multi
    def merge_bids(self):
        """
             To merge similar type of purchase orders.
        """
        ctx = dict(self._context)
        all_tender_ids = ctx.get('active_ids', []) or []
        if not all_tender_ids:
            raise Warning(_('You cannot proceed any tenders.'))
        new_tender_id = self._create_tender(all_tender_ids)
        if self.base_on == 'category':
            category_ids = [x.id for x in self.category_ids]
            self._merge_process_by_category(category_ids, all_tender_ids, new_tender_id)
        elif self.base_on == 'supplier':
            supplier_ids = [x.id for x in self.supplier_ids]
            self._merge_process_by_manufacturer(supplier_ids, all_tender_ids, new_tender_id)
        else:
            self.apply_common(all_tender_ids, new_tender_id)
  
        self.group_by_products(new_tender_id)
  
        return {
            'name': _('Purchase Requisition'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.requisition',
            'view_id': self.env.ref('purchase_requisition.view_purchase_requisition_form').id,
            'type': 'ir.actions.act_window',
            'res_id': new_tender_id
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
