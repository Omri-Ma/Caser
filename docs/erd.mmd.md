<!--

---
title: CaseHub ERD
---
erDiagram
audit_logs {
 INTEGER id PK
   VARCHAR(100) action 
   VARCHAR(255) target 
   INTEGER tenant_id 
   DATETIME timestamp 
   INTEGER user_id 
}
cases {
 INTEGER id PK
   DATETIME created_at 
   VARCHAR(11) status 
   INTEGER tenant_id 
   VARCHAR(255) title 
}
case_assignments {
 INTEGER id PK
   INTEGER case_id 
   INTEGER membership_id 
   INTEGER tenant_id 
}
documents {
 INTEGER id PK
   DATETIME archived_at 
   INTEGER case_id 
   VARCHAR(100) content_type 
   DATETIME created_at 
   BIGINT file_size 
   VARCHAR(500) file_url 
   VARCHAR(8) folder_type 
   VARCHAR(255) original_filename 
   INTEGER tenant_id 
   INTEGER uploaded_by 
}
identities {
 INTEGER id PK
   TEXT bio 
   VARCHAR(255) email 
   BOOLEAN is_super_admin 
   VARCHAR(255) name 
   VARCHAR(255) password_hash 
   VARCHAR(500) photo_url 
   INTEGER token_version 
}
memberships {
 INTEGER id PK
   BOOLEAN active 
   INTEGER identity_id 
   VARCHAR(14) role 
   BOOLEAN show_on_public_page 
   INTEGER tenant_id 
}
narratives {
 INTEGER id PK
   INTEGER case_id 
   DATETIME created_at 
   TEXT generated_text 
   INTEGER tenant_id 
   NUMERIC(10,_2) total_fee 
   NUMERIC(8,_2) total_hours 
}
settings {
 INTEGER id PK
   VARCHAR(100) key 
   INTEGER tenant_id 
   TEXT value 
}
subscriptions {
 INTEGER id PK
   BOOLEAN active 
   DATE end_date 
   VARCHAR(10) plan 
   DATE start_date 
   INTEGER tenant_id 
}
tenants {
 INTEGER id PK
   BOOLEAN active 
   VARCHAR(500) logo_url 
   VARCHAR(255) name 
   VARCHAR(7) primary_color 
   VARCHAR(63) subdomain 
}
work_logs {
 INTEGER id PK
   INTEGER case_id 
   DATE date 
   VARCHAR(1000) description 
   NUMERIC(6,_2) hours 
   INTEGER lawyer_id 
   VARCHAR(12) source 
   INTEGER tenant_id 
}
tenants 1--0+ audit_logs : has
memberships 1--0+ audit_logs : has
tenants 1--0+ cases : has
memberships 1--0+ case_assignments : has
tenants 1--0+ case_assignments : has
cases 1--0+ case_assignments : has
tenants 1--0+ documents : has
cases 1--0+ documents : has
memberships 1--0+ documents : has
identities 1--0+ memberships : has
tenants 1--0+ memberships : has
tenants 1--0+ narratives : has
cases 1--0+ narratives : has
tenants 1--0+ settings : has
tenants 1--0+ subscriptions : has
cases 1--0+ work_logs : has
memberships 1--0+ work_logs : has
tenants 1--0+ work_logs : has


-->
![](https://mermaid.ink/img/LS0tCnRpdGxlOiBDYXNlSHViIEVSRAotLS0KZXJEaWFncmFtCmF1ZGl0X2xvZ3MgewogSU5URUdFUiBpZCBQSwogICBWQVJDSEFSKDEwMCkgYWN0aW9uIAogICBWQVJDSEFSKDI1NSkgdGFyZ2V0IAogICBJTlRFR0VSIHRlbmFudF9pZCAKICAgREFURVRJTUUgdGltZXN0YW1wIAogICBJTlRFR0VSIHVzZXJfaWQgCn0KY2FzZXMgewogSU5URUdFUiBpZCBQSwogICBEQVRFVElNRSBjcmVhdGVkX2F0IAogICBWQVJDSEFSKDExKSBzdGF0dXMgCiAgIElOVEVHRVIgdGVuYW50X2lkIAogICBWQVJDSEFSKDI1NSkgdGl0bGUgCn0KY2FzZV9hc3NpZ25tZW50cyB7CiBJTlRFR0VSIGlkIFBLCiAgIElOVEVHRVIgY2FzZV9pZCAKICAgSU5URUdFUiBtZW1iZXJzaGlwX2lkIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQpkb2N1bWVudHMgewogSU5URUdFUiBpZCBQSwogICBEQVRFVElNRSBhcmNoaXZlZF9hdCAKICAgSU5URUdFUiBjYXNlX2lkIAogICBWQVJDSEFSKDEwMCkgY29udGVudF90eXBlIAogICBEQVRFVElNRSBjcmVhdGVkX2F0IAogICBCSUdJTlQgZmlsZV9zaXplIAogICBWQVJDSEFSKDUwMCkgZmlsZV91cmwgCiAgIFZBUkNIQVIoOCkgZm9sZGVyX3R5cGUgCiAgIFZBUkNIQVIoMjU1KSBvcmlnaW5hbF9maWxlbmFtZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIElOVEVHRVIgdXBsb2FkZWRfYnkgCn0KaWRlbnRpdGllcyB7CiBJTlRFR0VSIGlkIFBLCiAgIFRFWFQgYmlvIAogICBWQVJDSEFSKDI1NSkgZW1haWwgCiAgIEJPT0xFQU4gaXNfc3VwZXJfYWRtaW4gCiAgIFZBUkNIQVIoMjU1KSBuYW1lIAogICBWQVJDSEFSKDI1NSkgcGFzc3dvcmRfaGFzaCAKICAgVkFSQ0hBUig1MDApIHBob3RvX3VybCAKICAgSU5URUdFUiB0b2tlbl92ZXJzaW9uIAp9Cm1lbWJlcnNoaXBzIHsKIElOVEVHRVIgaWQgUEsKICAgQk9PTEVBTiBhY3RpdmUgCiAgIElOVEVHRVIgaWRlbnRpdHlfaWQgCiAgIFZBUkNIQVIoMTQpIHJvbGUgCiAgIEJPT0xFQU4gc2hvd19vbl9wdWJsaWNfcGFnZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KbmFycmF0aXZlcyB7CiBJTlRFR0VSIGlkIFBLCiAgIElOVEVHRVIgY2FzZV9pZCAKICAgREFURVRJTUUgY3JlYXRlZF9hdCAKICAgVEVYVCBnZW5lcmF0ZWRfdGV4dCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIE5VTUVSSUMoMTAsXzIpIHRvdGFsX2ZlZSAKICAgTlVNRVJJQyg4LF8yKSB0b3RhbF9ob3VycyAKfQpzZXR0aW5ncyB7CiBJTlRFR0VSIGlkIFBLCiAgIFZBUkNIQVIoMTAwKSBrZXkgCiAgIElOVEVHRVIgdGVuYW50X2lkIAogICBURVhUIHZhbHVlIAp9CnN1YnNjcmlwdGlvbnMgewogSU5URUdFUiBpZCBQSwogICBCT09MRUFOIGFjdGl2ZSAKICAgREFURSBlbmRfZGF0ZSAKICAgVkFSQ0hBUigxMCkgcGxhbiAKICAgREFURSBzdGFydF9kYXRlIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQp0ZW5hbnRzIHsKIElOVEVHRVIgaWQgUEsKICAgQk9PTEVBTiBhY3RpdmUgCiAgIFZBUkNIQVIoNTAwKSBsb2dvX3VybCAKICAgVkFSQ0hBUigyNTUpIG5hbWUgCiAgIFZBUkNIQVIoNykgcHJpbWFyeV9jb2xvciAKICAgVkFSQ0hBUig2Mykgc3ViZG9tYWluIAp9CndvcmtfbG9ncyB7CiBJTlRFR0VSIGlkIFBLCiAgIElOVEVHRVIgY2FzZV9pZCAKICAgREFURSBkYXRlIAogICBWQVJDSEFSKDEwMDApIGRlc2NyaXB0aW9uIAogICBOVU1FUklDKDYsXzIpIGhvdXJzIAogICBJTlRFR0VSIGxhd3llcl9pZCAKICAgVkFSQ0hBUigxMikgc291cmNlIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQp0ZW5hbnRzIDEtLTArIGF1ZGl0X2xvZ3MgOiBoYXMKbWVtYmVyc2hpcHMgMS0tMCsgYXVkaXRfbG9ncyA6IGhhcwp0ZW5hbnRzIDEtLTArIGNhc2VzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIGNhc2VfYXNzaWdubWVudHMgOiBoYXMKdGVuYW50cyAxLS0wKyBjYXNlX2Fzc2lnbm1lbnRzIDogaGFzCmNhc2VzIDEtLTArIGNhc2VfYXNzaWdubWVudHMgOiBoYXMKdGVuYW50cyAxLS0wKyBkb2N1bWVudHMgOiBoYXMKY2FzZXMgMS0tMCsgZG9jdW1lbnRzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIGRvY3VtZW50cyA6IGhhcwppZGVudGl0aWVzIDEtLTArIG1lbWJlcnNoaXBzIDogaGFzCnRlbmFudHMgMS0tMCsgbWVtYmVyc2hpcHMgOiBoYXMKdGVuYW50cyAxLS0wKyBuYXJyYXRpdmVzIDogaGFzCmNhc2VzIDEtLTArIG5hcnJhdGl2ZXMgOiBoYXMKdGVuYW50cyAxLS0wKyBzZXR0aW5ncyA6IGhhcwp0ZW5hbnRzIDEtLTArIHN1YnNjcmlwdGlvbnMgOiBoYXMKY2FzZXMgMS0tMCsgd29ya19sb2dzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIHdvcmtfbG9ncyA6IGhhcwp0ZW5hbnRzIDEtLTArIHdvcmtfbG9ncyA6IGhhcwo=)
