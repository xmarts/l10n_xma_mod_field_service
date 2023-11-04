# -*- coding: utf-8 -*-
{
    'name': " mod field_service",

    'summary': """""",

    'description': """
    """,

    'author': "XMARTS",
    'website': "",
    'category': 'Accounting',
    'version': '1.0.0',
    'depends': ['base', 'sale','industry_fsm', 'helpdesk','project', 'partner_names', 'xmart_hospital'],
    'data': [
        'security/ir.model.access.csv',
        #'views/res_currency_rate_inherit.xml',
        'views/res_currency_inherit.xml',
        'views/project_task_inherit.xml',
        'views/ticket.xml',
        
    ],
}
