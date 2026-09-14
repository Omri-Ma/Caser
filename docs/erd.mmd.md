<!--

---
title: Caser ERD
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
case_tags {
 INTEGER id PK
   INTEGER case_id 
   VARCHAR(11) practice_area 
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
   DATETIME last_login_at 
   VARCHAR(255) name 
   VARCHAR(255) password_hash 
   VARCHAR(500) photo_url 
   INTEGER token_version 
   INTEGER years_of_experience 
}
memberships {
 INTEGER id PK
   BOOLEAN active 
   NUMERIC(8,_2) hourly_rate 
   INTEGER identity_id 
   BOOLEAN is_manager 
   VARCHAR(14) role 
   BOOLEAN show_on_public_page 
   INTEGER tenant_id 
}
membership_invites {
 INTEGER id PK
   DATETIME created_at 
   VARCHAR(255) email 
   INTEGER invited_by 
   DATETIME responded_at 
   VARCHAR(14) role 
   VARCHAR(8) status 
   INTEGER tenant_id 
}
narratives {
 INTEGER id PK
   INTEGER case_id 
   DATETIME created_at 
   TEXT generated_text 
   VARCHAR(2) language 
   DATE period_end 
   DATE period_start 
   INTEGER tenant_id 
   NUMERIC(10,_2) total_fee 
   NUMERIC(8,_2) total_hours 
}
password_reset_tokens {
 INTEGER id PK
   DATETIME expires_at 
   INTEGER identity_id 
   VARCHAR(255) token_hash 
   DATETIME used_at 
}
platform_audit_logs {
 INTEGER id PK
   VARCHAR(100) action 
   INTEGER identity_id 
   INTEGER target_tenant_id 
   DATETIME timestamp 
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
   DATETIME created_at 
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
cases 1--0+ case_assignments : has
tenants 1--0+ case_assignments : has
tenants 1--0+ case_tags : has
cases 1--0+ case_tags : has
cases 1--0+ documents : has
memberships 1--0+ documents : has
tenants 1--0+ documents : has
identities 1--0+ memberships : has
tenants 1--0+ memberships : has
memberships 1--0+ membership_invites : has
tenants 1--0+ membership_invites : has
tenants 1--0+ narratives : has
cases 1--0+ narratives : has
identities 1--0+ password_reset_tokens : has
tenants 1--0+ platform_audit_logs : has
identities 1--0+ platform_audit_logs : has
tenants 1--0+ settings : has
tenants 1--0+ subscriptions : has
tenants 1--0+ work_logs : has
cases 1--0+ work_logs : has
memberships 1--0+ work_logs : has


-->
![](https://mermaid.ink/img/LS0tCnRpdGxlOiBDYXNlciBFUkQKLS0tCmVyRGlhZ3JhbQphdWRpdF9sb2dzIHsKIElOVEVHRVIgaWQgUEsKICAgVkFSQ0hBUigxMDApIGFjdGlvbiAKICAgVkFSQ0hBUigyNTUpIHRhcmdldCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIERBVEVUSU1FIHRpbWVzdGFtcCAKICAgSU5URUdFUiB1c2VyX2lkIAp9CmNhc2VzIHsKIElOVEVHRVIgaWQgUEsKICAgREFURVRJTUUgY3JlYXRlZF9hdCAKICAgVkFSQ0hBUigxMSkgc3RhdHVzIAogICBJTlRFR0VSIHRlbmFudF9pZCAKICAgVkFSQ0hBUigyNTUpIHRpdGxlIAp9CmNhc2VfYXNzaWdubWVudHMgewogSU5URUdFUiBpZCBQSwogICBJTlRFR0VSIGNhc2VfaWQgCiAgIElOVEVHRVIgbWVtYmVyc2hpcF9pZCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KY2FzZV90YWdzIHsKIElOVEVHRVIgaWQgUEsKICAgSU5URUdFUiBjYXNlX2lkIAogICBWQVJDSEFSKDExKSBwcmFjdGljZV9hcmVhIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQpkb2N1bWVudHMgewogSU5URUdFUiBpZCBQSwogICBEQVRFVElNRSBhcmNoaXZlZF9hdCAKICAgSU5URUdFUiBjYXNlX2lkIAogICBWQVJDSEFSKDEwMCkgY29udGVudF90eXBlIAogICBEQVRFVElNRSBjcmVhdGVkX2F0IAogICBCSUdJTlQgZmlsZV9zaXplIAogICBWQVJDSEFSKDUwMCkgZmlsZV91cmwgCiAgIFZBUkNIQVIoOCkgZm9sZGVyX3R5cGUgCiAgIFZBUkNIQVIoMjU1KSBvcmlnaW5hbF9maWxlbmFtZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIElOVEVHRVIgdXBsb2FkZWRfYnkgCn0KaWRlbnRpdGllcyB7CiBJTlRFR0VSIGlkIFBLCiAgIFRFWFQgYmlvIAogICBWQVJDSEFSKDI1NSkgZW1haWwgCiAgIEJPT0xFQU4gaXNfc3VwZXJfYWRtaW4gCiAgIERBVEVUSU1FIGxhc3RfbG9naW5fYXQgCiAgIFZBUkNIQVIoMjU1KSBuYW1lIAogICBWQVJDSEFSKDI1NSkgcGFzc3dvcmRfaGFzaCAKICAgVkFSQ0hBUig1MDApIHBob3RvX3VybCAKICAgSU5URUdFUiB0b2tlbl92ZXJzaW9uIAogICBJTlRFR0VSIHllYXJzX29mX2V4cGVyaWVuY2UgCn0KbWVtYmVyc2hpcHMgewogSU5URUdFUiBpZCBQSwogICBCT09MRUFOIGFjdGl2ZSAKICAgTlVNRVJJQyg4LF8yKSBob3VybHlfcmF0ZSAKICAgSU5URUdFUiBpZGVudGl0eV9pZCAKICAgQk9PTEVBTiBpc19tYW5hZ2VyIAogICBWQVJDSEFSKDE0KSByb2xlIAogICBCT09MRUFOIHNob3dfb25fcHVibGljX3BhZ2UgCiAgIElOVEVHRVIgdGVuYW50X2lkIAp9Cm1lbWJlcnNoaXBfaW52aXRlcyB7CiBJTlRFR0VSIGlkIFBLCiAgIERBVEVUSU1FIGNyZWF0ZWRfYXQgCiAgIFZBUkNIQVIoMjU1KSBlbWFpbCAKICAgSU5URUdFUiBpbnZpdGVkX2J5IAogICBEQVRFVElNRSByZXNwb25kZWRfYXQgCiAgIFZBUkNIQVIoMTQpIHJvbGUgCiAgIFZBUkNIQVIoOCkgc3RhdHVzIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQpuYXJyYXRpdmVzIHsKIElOVEVHRVIgaWQgUEsKICAgSU5URUdFUiBjYXNlX2lkIAogICBEQVRFVElNRSBjcmVhdGVkX2F0IAogICBURVhUIGdlbmVyYXRlZF90ZXh0IAogICBWQVJDSEFSKDIpIGxhbmd1YWdlIAogICBEQVRFIHBlcmlvZF9lbmQgCiAgIERBVEUgcGVyaW9kX3N0YXJ0IAogICBJTlRFR0VSIHRlbmFudF9pZCAKICAgTlVNRVJJQygxMCxfMikgdG90YWxfZmVlIAogICBOVU1FUklDKDgsXzIpIHRvdGFsX2hvdXJzIAp9CnBhc3N3b3JkX3Jlc2V0X3Rva2VucyB7CiBJTlRFR0VSIGlkIFBLCiAgIERBVEVUSU1FIGV4cGlyZXNfYXQgCiAgIElOVEVHRVIgaWRlbnRpdHlfaWQgCiAgIFZBUkNIQVIoMjU1KSB0b2tlbl9oYXNoIAogICBEQVRFVElNRSB1c2VkX2F0IAp9CnBsYXRmb3JtX2F1ZGl0X2xvZ3MgewogSU5URUdFUiBpZCBQSwogICBWQVJDSEFSKDEwMCkgYWN0aW9uIAogICBJTlRFR0VSIGlkZW50aXR5X2lkIAogICBJTlRFR0VSIHRhcmdldF90ZW5hbnRfaWQgCiAgIERBVEVUSU1FIHRpbWVzdGFtcCAKfQpzZXR0aW5ncyB7CiBJTlRFR0VSIGlkIFBLCiAgIFZBUkNIQVIoMTAwKSBrZXkgCiAgIElOVEVHRVIgdGVuYW50X2lkIAogICBURVhUIHZhbHVlIAp9CnN1YnNjcmlwdGlvbnMgewogSU5URUdFUiBpZCBQSwogICBCT09MRUFOIGFjdGl2ZSAKICAgREFURSBlbmRfZGF0ZSAKICAgVkFSQ0hBUigxMCkgcGxhbiAKICAgREFURSBzdGFydF9kYXRlIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQp0ZW5hbnRzIHsKIElOVEVHRVIgaWQgUEsKICAgQk9PTEVBTiBhY3RpdmUgCiAgIERBVEVUSU1FIGNyZWF0ZWRfYXQgCiAgIFZBUkNIQVIoNTAwKSBsb2dvX3VybCAKICAgVkFSQ0hBUigyNTUpIG5hbWUgCiAgIFZBUkNIQVIoNykgcHJpbWFyeV9jb2xvciAKICAgVkFSQ0hBUig2Mykgc3ViZG9tYWluIAp9CndvcmtfbG9ncyB7CiBJTlRFR0VSIGlkIFBLCiAgIElOVEVHRVIgY2FzZV9pZCAKICAgREFURSBkYXRlIAogICBWQVJDSEFSKDEwMDApIGRlc2NyaXB0aW9uIAogICBOVU1FUklDKDYsXzIpIGhvdXJzIAogICBJTlRFR0VSIGxhd3llcl9pZCAKICAgVkFSQ0hBUigxMikgc291cmNlIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQp0ZW5hbnRzIDEtLTArIGF1ZGl0X2xvZ3MgOiBoYXMKbWVtYmVyc2hpcHMgMS0tMCsgYXVkaXRfbG9ncyA6IGhhcwp0ZW5hbnRzIDEtLTArIGNhc2VzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIGNhc2VfYXNzaWdubWVudHMgOiBoYXMKY2FzZXMgMS0tMCsgY2FzZV9hc3NpZ25tZW50cyA6IGhhcwp0ZW5hbnRzIDEtLTArIGNhc2VfYXNzaWdubWVudHMgOiBoYXMKdGVuYW50cyAxLS0wKyBjYXNlX3RhZ3MgOiBoYXMKY2FzZXMgMS0tMCsgY2FzZV90YWdzIDogaGFzCmNhc2VzIDEtLTArIGRvY3VtZW50cyA6IGhhcwptZW1iZXJzaGlwcyAxLS0wKyBkb2N1bWVudHMgOiBoYXMKdGVuYW50cyAxLS0wKyBkb2N1bWVudHMgOiBoYXMKaWRlbnRpdGllcyAxLS0wKyBtZW1iZXJzaGlwcyA6IGhhcwp0ZW5hbnRzIDEtLTArIG1lbWJlcnNoaXBzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIG1lbWJlcnNoaXBfaW52aXRlcyA6IGhhcwp0ZW5hbnRzIDEtLTArIG1lbWJlcnNoaXBfaW52aXRlcyA6IGhhcwp0ZW5hbnRzIDEtLTArIG5hcnJhdGl2ZXMgOiBoYXMKY2FzZXMgMS0tMCsgbmFycmF0aXZlcyA6IGhhcwppZGVudGl0aWVzIDEtLTArIHBhc3N3b3JkX3Jlc2V0X3Rva2VucyA6IGhhcwp0ZW5hbnRzIDEtLTArIHBsYXRmb3JtX2F1ZGl0X2xvZ3MgOiBoYXMKaWRlbnRpdGllcyAxLS0wKyBwbGF0Zm9ybV9hdWRpdF9sb2dzIDogaGFzCnRlbmFudHMgMS0tMCsgc2V0dGluZ3MgOiBoYXMKdGVuYW50cyAxLS0wKyBzdWJzY3JpcHRpb25zIDogaGFzCnRlbmFudHMgMS0tMCsgd29ya19sb2dzIDogaGFzCmNhc2VzIDEtLTArIHdvcmtfbG9ncyA6IGhhcwptZW1iZXJzaGlwcyAxLS0wKyB3b3JrX2xvZ3MgOiBoYXMK)
