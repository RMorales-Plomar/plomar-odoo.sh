from odoo import models, fields, api
from datetime import timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        delivery_date = fields.Datetime.now() + timedelta(days=5)
        delivery_date = date_action

        self.write({
            'commitment_date': delivery_date
        })

        return res
