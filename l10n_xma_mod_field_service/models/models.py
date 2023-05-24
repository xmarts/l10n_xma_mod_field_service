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
import logging
from odoo.addons.payment import utils as payment_utils

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


    

class ProjectTask(models.Model):
    _inherit = "project.task"
    
    date_ahora = fields.Datetime()
    user_id = fields.Many2one('res.users')
    timeline_ids = fields.One2many('project.task.timeline','timeline_id')
    
    @api.onchange('stage_id')
    def test_mod(self):
        test = 0
        for a in self:
            test = a._origin.id
            active_id =  self.env.context.get('active_id')
            _logger.debug('//////////////////////////////////Create')
            rounding_line_vals = {
                'timeline_id_b': a._origin.id,
                'stage_id': a.project_id.stage_id.id,
                #'Datetime': a.date_ahora,
                'users_id': a.user_id.id,
            }
        
        self.timeline_ids.create(rounding_line_vals)
            
            
class ProjectTaskTimeline(models.Model):
    _name = "project.task.timeline"
    
    timeline_id = fields.Many2one('project.task')
    
    timeline_id_b = fields.Many2one('project.task')
    
    name=fields.Char()
    stage_id = fields.Many2one('project.project.stage', groups="project.group_project_stages")
    Datetime = fields.Datetime()
    users_id = fields.Many2one('res.users')
    

    
    
    