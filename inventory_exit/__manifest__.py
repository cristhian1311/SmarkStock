{
    'name': 'Inventory Exits',
    'version': '1.0',
    'depends': ['base', 'product_register'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_exit_views.xml',
    ],
    'installable': True,
}