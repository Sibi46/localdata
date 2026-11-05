import io
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client,TestCase
from django.urls import reverse
from openpyxl import Workbook,load_workbook
from .models import CompanyProfile,ShopDirectoryEntry,ShopProfile,User


def workbook_file(rows):
    book=Workbook();sheet=book.active
    for row in rows:sheet.append(row)
    stream=io.BytesIO();book.save(stream);book.close()
    return SimpleUploadedFile('shops.xlsx',stream.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class ShopDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=User.objects.create_user('directory-admin',admin_role='super_admin')
        cls.owner=User.objects.create_user('directory-owner',first_name='Priya',phone='9876501122',pincode='604408',city='Vandavasi',user_type='individual')
        cls.other=User.objects.create_user('directory-other',phone='9876501133')

    def upload(self,rows):
        self.client.force_login(self.admin)
        return self.client.post(reverse('shop_directory'),{'file':workbook_file(rows)})

    def entry(self,**values):
        data={'name':'Priya Stores','normalized_name':'priya stores','phone':self.owner.phone,'pincode':'604408','city':'Vandavasi','category':'Groceries'}
        data.update(values)
        return ShopDirectoryEntry.objects.create(**data)

    def business_data(self,entry,**values):
        data={'account_type':'shop','name':entry.name,'pincode':'604408','city':'Vandavasi','category':entry.category,'directory_entry':entry.pk}
        data.update(values)
        return data

    def test_upload_requires_superadmin_and_template_is_excel(self):
        self.assertEqual(self.client.get(reverse('shop_directory')).status_code,302)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('shop_directory')).status_code,403)
        self.assertEqual(self.client.get(reverse('shop_directory_template')).status_code,403)
        self.client.force_login(self.admin)
        response=self.client.get(reverse('shop_directory_template'))
        self.assertEqual(response.status_code,200)
        book=load_workbook(io.BytesIO(response.content),read_only=True)
        self.assertEqual(next(book.active.values)[:2],('Shop Name','Phone'));book.close()

    def test_excel_import_normalizes_phone_and_accepts_optional_fields(self):
        response=self.upload([['Shop Name','Ph No','Pincode','City','Category','Address'],['Priya Stores','+91 98765 01122',604408,'Vandavasi','Groceries','Market Road']])
        self.assertEqual(response.status_code,302)
        entry=ShopDirectoryEntry.objects.get()
        self.assertEqual((entry.name,entry.phone,entry.pincode,entry.city,entry.uploaded_by_id),('Priya Stores',self.owner.phone,'604408','Vandavasi',self.admin.pk))
        self.assertFalse(CompanyProfile.objects.exists())
        self.assertEqual(User.objects.count(),3)

    def test_invalid_phone_is_saved_for_review_without_rejecting_good_rows(self):
        response=self.upload([['Shop Name','Phone'],['Good shop',9876501122],['Bad shop','123']])
        self.assertEqual(response.status_code,302)
        bad=ShopDirectoryEntry.objects.get(name='Bad shop')
        self.assertEqual((bad.phone,bad.source_phone),('','123'))
        self.assertTrue(bad.phone_note)
        self.assertEqual(ShopDirectoryEntry.objects.count(),2)

    def test_missing_shop_name_still_prevents_partial_import(self):
        response=self.upload([['Shop Name','Phone'],['Good shop',9876501122],['',9876501133]])
        self.assertContains(response,'Row 3:')
        self.assertFalse(ShopDirectoryEntry.objects.exists())

    def test_bad_headers_unsupported_and_corrupt_files_show_errors(self):
        response=self.upload([['Something','Else'],['Shop','9876501122']])
        self.assertContains(response,'first row must contain Shop Name and Phone')
        for name in ['old.xls','broken.xlsx']:
            response=self.client.post(reverse('shop_directory'),{'file':SimpleUploadedFile(name,b'invalid')})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(ShopDirectoryEntry.objects.exists())

    def test_reupload_and_duplicate_rows_do_not_duplicate_shops(self):
        self.upload([['Shop Name','Phone','City'],['Priya Stores',9876501122,'Vandavasi'],['Priya Stores',9876501122,'Vandavasi']])
        self.upload([['Shop Name','Phone'],['PRIYA STORES',9876501122]])
        self.assertEqual(ShopDirectoryEntry.objects.count(),1)
        self.assertEqual(ShopDirectoryEntry.objects.get().city,'Vandavasi')

    def test_csv_import_and_numeric_excel_phone(self):
        self.client.force_login(self.admin)
        response=self.client.post(reverse('shop_directory'),{'file':SimpleUploadedFile('shops.csv',b'Shop Name,Phone\nCSV Shop,+91 9876501122\n')})
        self.assertEqual(response.status_code,302)
        self.assertEqual(ShopDirectoryEntry.objects.get().phone,self.owner.phone)

    def test_search_by_name_or_phone_only_returns_account_matches(self):
        own=self.entry();self.entry(name='Other Priya Store',normalized_name='other priya store',phone=self.other.phone)
        self.client.force_login(self.owner)
        for query in ['Priya','9876501122','+91 98765 01122']:
            response=self.client.get(reverse('shop_directory_search'),{'q':query})
            self.assertEqual([entry['id'] for entry in response.json()['results']],[own.pk])
            self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.client.get(reverse('shop_directory_search'),{'q':self.other.phone}).json()['results'],[])

    def test_selection_claims_shop_and_keeps_account_identity(self):
        entry=self.entry();self.client.force_login(self.owner)
        response=self.client.post(reverse('business_create'),self.business_data(entry,name='Forged name',phone=self.other.phone))
        self.assertEqual(response.status_code,302)
        entry.refresh_from_db();self.owner.refresh_from_db()
        self.assertEqual(entry.registered_shop.company_name,'Priya Stores')
        self.assertEqual(entry.registered_shop.user_id,self.owner.pk)
        self.assertEqual(self.owner.phone,'9876501122')
        self.assertEqual(ShopProfile.objects.get(user=self.owner).shop_name,'Priya Stores')
        self.assertContains(self.client.get(reverse('shop_directory_search'),{'q':'Priya'}),'"results": []')
        self.client.post(reverse('business_create'),self.business_data(entry))
        self.assertEqual(CompanyProfile.objects.count(),1)

    def test_tampered_selection_cannot_claim_another_phones_shop(self):
        entry=self.entry(phone=self.other.phone);self.client.force_login(self.owner)
        response=self.client.post(reverse('business_create'),self.business_data(entry))
        self.assertContains(response,'unavailable for your account')
        self.assertFalse(CompanyProfile.objects.exists())

    def test_claimed_listing_cannot_be_claimed_again_or_overwritten(self):
        company=CompanyProfile.objects.create(user=self.other,company_name='Original Shop')
        entry=self.entry(registered_shop=company)
        self.upload([['Shop Name','Phone','City'],['Priya Stores',self.owner.phone,'Changed town']])
        entry.refresh_from_db();self.assertEqual(entry.city,'Vandavasi')
        self.client.force_login(self.owner)
        response=self.client.post(reverse('business_create'),self.business_data(entry))
        self.assertContains(response,'unavailable for your account')
        self.assertFalse(CompanyProfile.objects.filter(user=self.owner).exists())

    def test_manual_shop_registration_still_works(self):
        self.client.force_login(self.owner)
        response=self.client.post(reverse('business_create'),{'account_type':'shop','name':'New Shop','pincode':'604408','city':'Vandavasi'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(CompanyProfile.objects.get(user=self.owner).company_name,'New Shop')

    def test_multiple_contacts_and_reversed_reupload_keep_one_listing(self):
        self.upload([['Business Name','Phone Number'],['Priya Stores','9876501122, +91 9876501133; 9876501122']])
        entry=ShopDirectoryEntry.objects.get()
        self.assertEqual(entry.alternate_phones,[self.other.phone])
        self.upload([['Business Name','Phone Number'],['Priya Stores','9876501133 / 9876501122']])
        self.assertEqual(ShopDirectoryEntry.objects.count(),1)
        entry.refresh_from_db()
        self.assertEqual((entry.phone,entry.alternate_phones),(self.owner.phone,[self.other.phone]))

    def test_phone_formats_do_not_invent_or_trim_digits(self):
        from .shop_directory import parse_phone_cell
        for source in ['98765 01122 98765 01133','9876501122 9876501133','9876501122\n9876501133']:
            self.assertEqual(parse_phone_cell(source)[0],[self.owner.phone,self.other.phone])
        for source in [None,'123',98765011223,9.87650112233e11,'-9876501122']:
            phones,original,note=parse_phone_cell(source)
            self.assertEqual(phones,[])
            self.assertTrue(note)
        phones,original,note=parse_phone_cell('123, 9876501133')
        self.assertEqual(phones,[self.other.phone]);self.assertTrue(note)

    def test_blank_and_malformed_phones_are_reviewable_but_not_claimable(self):
        self.upload([['Shop Name','Phone'],['Blank Shop',None],['Malformed Shop','123']])
        response=self.client.get(reverse('shop_directory'),{'review':'1'})
        self.assertEqual(response.context['review_count'],2)
        entry=ShopDirectoryEntry.objects.get(name='Blank Shop')
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('shop_directory_search'),{'q':'Shop'}).json()['results'],[])
        self.assertContains(self.client.post(reverse('business_create'),self.business_data(entry)),'unavailable for your account')
        self.assertFalse(CompanyProfile.objects.exists())

    def test_secondary_contact_can_claim_but_search_does_not_leak_other_contacts(self):
        entry=self.entry(alternate_phones=[self.other.phone],source_phone='private original cell')
        self.client.force_login(self.other)
        response=self.client.get(reverse('shop_directory_search'),{'q':'Priya'})
        result=response.json()['results'][0]
        self.assertEqual(result['phone'],self.other.phone)
        self.assertNotIn(self.owner.phone,response.content.decode())
        self.assertNotIn('source_phone',result);self.assertNotIn('alternate_phones',result)
        self.assertEqual(self.client.post(reverse('business_create'),self.business_data(entry)).status_code,302)
        entry.refresh_from_db();self.assertEqual(entry.registered_shop.user_id,self.other.pk)
        self.client.force_login(self.owner)
        self.assertContains(self.client.post(reverse('business_create'),self.business_data(entry)),'unavailable for your account')
        self.assertEqual(CompanyProfile.objects.count(),1)

    def test_admin_correction_is_post_only_csrf_protected_and_private(self):
        entry=self.entry(phone='',source_phone='123',phone_note='Needs review')
        url=reverse('shop_directory_phones',args=[entry.pk])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(url,{'phones':self.owner.phone}).status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code,405)
        client=Client(enforce_csrf_checks=True);client.force_login(self.admin)
        self.assertEqual(client.post(url,{'phones':self.owner.phone}).status_code,403)
        self.assertEqual(self.client.post(url,{'phones':'123'}).status_code,302)
        entry.refresh_from_db();self.assertEqual(entry.phone,'')
        self.assertEqual(self.client.post(url,{'phones':self.owner.phone}).status_code,302)
        entry.refresh_from_db();self.assertEqual(entry.phone,self.owner.phone)
        self.assertEqual(entry.source_phone,'123');self.assertEqual(entry.phone_note,'')
        self.assertTrue(entry.contacts_reviewed)

    def test_reupload_cannot_restore_a_contact_removed_by_admin(self):
        source='9876501122, 9876501133'
        self.upload([['Shop Name','Phone'],['Priya Stores',source]])
        entry=ShopDirectoryEntry.objects.get()
        self.client.post(reverse('shop_directory_phones',args=[entry.pk]),{'phones':self.other.phone})
        self.upload([['Shop Name','Phone'],['Priya Stores',source]])
        entry.refresh_from_db()
        self.assertEqual((entry.phone,entry.alternate_phones),(self.other.phone,[]))
        self.assertEqual(ShopDirectoryEntry.objects.count(),1)

    def test_corrected_missing_phone_is_not_duplicated_on_reupload(self):
        self.upload([['Shop Name','Phone'],['Priya Stores',None]])
        entry=ShopDirectoryEntry.objects.get()
        self.client.post(reverse('shop_directory_phones',args=[entry.pk]),{'phones':self.owner.phone})
        self.upload([['Shop Name','Phone'],['Priya Stores',None]])
        entry.refresh_from_db()
        self.assertEqual(entry.phone,self.owner.phone)
        self.assertEqual(entry.phone_note,'')
        self.assertEqual(ShopDirectoryEntry.objects.count(),1)

    def test_registered_contacts_cannot_be_edited(self):
        company=CompanyProfile.objects.create(user=self.owner,company_name='Original Shop')
        entry=self.entry(registered_shop=company)
        self.client.force_login(self.admin)
        self.client.post(reverse('shop_directory_phones',args=[entry.pk]),{'phones':self.other.phone})
        entry.refresh_from_db();self.assertEqual(entry.phone,self.owner.phone)

    def test_same_name_invalid_sources_merge_without_unique_constraint_error(self):
        self.upload([['Shop Name','Phone'],['No Contact','123'],['No Contact','456']])
        self.assertEqual(ShopDirectoryEntry.objects.count(),1)
