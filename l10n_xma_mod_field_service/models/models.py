# -*- coding: utf-8 -*-
from datetime import timedelta
from itertools import groupby
from markupsafe import Markup

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.osv import expression
from odoo.tools import float_is_zero, format_amount, format_date, html_keep_url, is_html_empty
from odoo.tools.sql import create_index

from odoo.addons.payment import utils as payment_utils


class helpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"
    
    @api.onchange('user_id')
    def create_ticket(self):
        if self.team_id.id == 6:
            self.env['project.task'].create({
                                            'name': '{}'.format(self.name),
                                            #'team_id': 1,
                                            #'priority': '3',
                                            'partner_id': self.partner_id.id,
                                            #'partner_name': self.partner_id.name,
                                            #'partner_email': self.partner_id.email,
                                            #'partner_phone': self.partner_id.phone,
                                            #'ref_sale': self.id,
                                            })
    
#class helpdeskTic(models.Model):
   # _inherit = "helpdesk.ticket"
    
    #ref_sale = fields.Many2one('sale.order')