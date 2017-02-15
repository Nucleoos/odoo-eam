# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo
#    Copyright (C) 2017 CodUP (<http://codup.com>).
#
##############################################################################

from odoo import api, fields, models, tools, _

class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    def _check_category(self):
        parts_category = self.env.ref('mro.product_category_mro', raise_if_not_found=False)
        for product in self:
            if parts_category:
                if product.categ_id.id == parts_category.id:
                    product.isParts = True
            else:
                product.isParts = False

    @api.model
    def update_template_isparts(self):
        parts_category = self.env.ref('mro.product_category_mro', raise_if_not_found=False)
        all_products =  self.sudo().search([])
        for product in all_products:
            is_part = False
            if parts_category and parts_category.id == product.categ_id.id:
                is_part = True
            product.isParts = is_part

    isParts = fields.Boolean(compute='_check_category', store=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: