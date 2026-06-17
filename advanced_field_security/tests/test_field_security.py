from odoo.tests.common import TransactionCase
from lxml import etree

class TestFieldSecurity(TransactionCase):

    def setUp(self):
        super(TestFieldSecurity, self).setUp()
        
        # Create a test group and a test user
        self.test_group = self.env['res.groups'].create({
            'name': 'Test Restricted Group'
        })
        
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user_field_sec',
            'groups_id': [(4, self.test_group.id), (4, self.env.ref('base.group_user').id)]
        })
        
        # Get model and field IDs for res.partner's 'phone' field
        self.partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        self.phone_field = self.env['ir.model.fields'].search([
            ('model_id', '=', self.partner_model.id),
            ('name', '=', 'phone')
        ], limit=1)

    def test_01_invisible_rule_view(self):
        """Test that an invisible rule modifies get_view architecture."""
        self.assertTrue(self.phone_field, "Ensure phone field exists in ir.model.fields")
        
        # Create a rule to hide 'phone' from 'test_group'
        self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'invisible'
        })
        
        # Fetch the view as the test user
        view_info = self.env['res.partner'].with_user(self.test_user).get_view(view_type='form')
        arch_node = etree.fromstring(view_info['arch'])
        
        # Find the phone field in the XML
        phone_nodes = arch_node.xpath('//field[@name="phone"]')
        self.assertTrue(phone_nodes, "Phone field should exist in the partner form view")
        
        # Verify it has invisible="1"
        for node in phone_nodes:
            self.assertEqual(node.get('invisible'), '1', "Phone field should be invisible for test user")
            
        # Verify for superuser it is NOT invisible
        admin_view = self.env['res.partner'].get_view(view_type='form')
        admin_arch = etree.fromstring(admin_view['arch'])
        admin_phone_nodes = admin_arch.xpath('//field[@name="phone"]')
        for node in admin_phone_nodes:
            self.assertNotEqual(node.get('invisible'), '1', "Phone field should NOT be invisible for admin")

    def test_02_readonly_rule_fields_get(self):
        """Test that a readonly rule modifies fields_get output."""
        self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'readonly'
        })
        
        # Fetch fields_get as test user
        fields_info = self.env['res.partner'].with_user(self.test_user).fields_get(allfields=['phone'])
        self.assertTrue(fields_info.get('phone', {}).get('readonly'), "Phone field should be readonly in fields_get")
        
        # Fetch as admin
        admin_fields = self.env['res.partner'].fields_get(allfields=['phone'])
        self.assertFalse(admin_fields.get('phone', {}).get('readonly', False), "Phone field should not be readonly for admin")

    def test_03_required_rule_view(self):
        """Test that a required rule modifies get_view architecture."""
        self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'required'
        })
        
        view_info = self.env['res.partner'].with_user(self.test_user).get_view(view_type='form')
        arch_node = etree.fromstring(view_info['arch'])
        
        phone_nodes = arch_node.xpath('//field[@name="phone"]')
        for node in phone_nodes:
            self.assertEqual(node.get('required'), '1', "Phone field should be required for test user")
            
    def test_04_invisible_rule_fields_get(self):
        """Test that an invisible rule completely removes the field from fields_get."""
        self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'invisible'
        })
        
        fields_info = self.env['res.partner'].with_user(self.test_user).fields_get(allfields=['phone'])
        self.assertNotIn('phone', fields_info, "Phone field should be completely missing from fields_get for test user")
