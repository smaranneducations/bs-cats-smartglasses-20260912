from types import SimpleNamespace as Item
import unittest
from packages.audience.public_evidence import published_cards


class PublishedEvidenceTests(unittest.TestCase):
    def values(self, status='published', product_version=1, current_version=1, product_status='active'):
        card=Item(status=Item(value=status),payload={'product_id':'product_one','product_version':product_version})
        product=Item(object_type='product',object_id='product_one',version=current_version,status=Item(value=product_status),title='Publicly referenced product',payload={'private_notes':'must never appear'})
        store=Item(list_objects=lambda **_: [card],get=lambda _: product)
        return published_cards(store,lambda _: {'claims':[{'statement':'Published statement'}]})

    def test_unpublished_card_is_not_exposed(self):self.assertEqual(self.values(status='captured'),[])
    def test_changed_product_invalidates_public_projection(self):self.assertEqual(self.values(current_version=2),[])
    def test_retired_product_is_not_exposed(self):self.assertEqual(self.values(product_status='archived'),[])
    def test_only_public_projection_and_identity_are_returned(self):
        result=self.values()[0]
        self.assertEqual(set(result),{'claims','product_id','product_version','product_title'})
        self.assertNotIn('private_notes',str(result))
