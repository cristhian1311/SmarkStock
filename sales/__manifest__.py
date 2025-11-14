{
    'name': 'Sales (Custom)',
    'version': '1.0',
    'depends': ['base', 'product_register', 'inventory_exit'],
    'data': [
        'security/ir.model.access.csv',
        'views/sales_views.xml',
    ],
    'installable': True,
}
