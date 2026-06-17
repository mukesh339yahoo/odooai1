{
    'name': 'Advanced Field-Level Security',
    'version': '1.0.0',
    'category': 'Administration/Security',
    'summary': 'Configure field-level security rules without custom code',
    'description': """
        This module allows administrators to configure field-level security
        (Invisible, Readonly, Required) dynamically based on User Groups
        without requiring any custom XML development.
    """,
    'author': 'Your Company',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/field_security_rule_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
