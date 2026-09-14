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
   INTEGER years_of_experience 
}
memberships {
 INTEGER id PK
   BOOLEAN active 
   INTEGER identity_id 
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
memberships 1--0+ documents : has
tenants 1--0+ documents : has
cases 1--0+ documents : has
tenants 1--0+ memberships : has
identities 1--0+ memberships : has
memberships 1--0+ membership_invites : has
tenants 1--0+ membership_invites : has
cases 1--0+ narratives : has
tenants 1--0+ narratives : has
identities 1--0+ password_reset_tokens : has
tenants 1--0+ settings : has
tenants 1--0+ subscriptions : has
tenants 1--0+ work_logs : has
cases 1--0+ work_logs : has
memberships 1--0+ work_logs : has


-->
![](https://mermaid.ink/img/LS0tCnRpdGxlOiBDYXNlciBFUkQKLS0tCmVyRGlhZ3JhbQphdWRpdF9sb2dzIHsKIElOVEVHRVIgaWQgUEsKICAgVkFSQ0hBUigxMDApIGFjdGlvbiAKICAgVkFSQ0hBUigyNTUpIHRhcmdldCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIERBVEVUSU1FIHRpbWVzdGFtcCAKICAgSU5URUdFUiB1c2VyX2lkIAp9CmNhc2VzIHsKIElOVEVHRVIgaWQgUEsKICAgREFURVRJTUUgY3JlYXRlZF9hdCAKICAgVkFSQ0hBUigxMSkgc3RhdHVzIAogICBJTlRFR0VSIHRlbmFudF9pZCAKICAgVkFSQ0hBUigyNTUpIHRpdGxlIAp9CmNhc2VfYXNzaWdubWVudHMgewogSU5URUdFUiBpZCBQSwogICBJTlRFR0VSIGNhc2VfaWQgCiAgIElOVEVHRVIgbWVtYmVyc2hpcF9pZCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KZG9jdW1lbnRzIHsKIElOVEVHRVIgaWQgUEsKICAgREFURVRJTUUgYXJjaGl2ZWRfYXQgCiAgIElOVEVHRVIgY2FzZV9pZCAKICAgVkFSQ0hBUigxMDApIGNvbnRlbnRfdHlwZSAKICAgREFURVRJTUUgY3JlYXRlZF9hdCAKICAgQklHSU5UIGZpbGVfc2l6ZSAKICAgVkFSQ0hBUig1MDApIGZpbGVfdXJsIAogICBWQVJDSEFSKDgpIGZvbGRlcl90eXBlIAogICBWQVJDSEFSKDI1NSkgb3JpZ2luYWxfZmlsZW5hbWUgCiAgIElOVEVHRVIgdGVuYW50X2lkIAogICBJTlRFR0VSIHVwbG9hZGVkX2J5IAp9CmlkZW50aXRpZXMgewogSU5URUdFUiBpZCBQSwogICBURVhUIGJpbyAKICAgVkFSQ0hBUigyNTUpIGVtYWlsIAogICBCT09MRUFOIGlzX3N1cGVyX2FkbWluIAogICBWQVJDSEFSKDI1NSkgbmFtZSAKICAgVkFSQ0hBUigyNTUpIHBhc3N3b3JkX2hhc2ggCiAgIFZBUkNIQVIoNTAwKSBwaG90b191cmwgCiAgIElOVEVHRVIgdG9rZW5fdmVyc2lvbiAKICAgSU5URUdFUiB5ZWFyc19vZl9leHBlcmllbmNlIAp9Cm1lbWJlcnNoaXBzIHsKIElOVEVHRVIgaWQgUEsKICAgQk9PTEVBTiBhY3RpdmUgCiAgIElOVEVHRVIgaWRlbnRpdHlfaWQgCiAgIFZBUkNIQVIoMTQpIHJvbGUgCiAgIEJPT0xFQU4gc2hvd19vbl9wdWJsaWNfcGFnZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KbWVtYmVyc2hpcF9pbnZpdGVzIHsKIElOVEVHRVIgaWQgUEsKICAgREFURVRJTUUgY3JlYXRlZF9hdCAKICAgVkFSQ0hBUigyNTUpIGVtYWlsIAogICBJTlRFR0VSIGludml0ZWRfYnkgCiAgIERBVEVUSU1FIHJlc3BvbmRlZF9hdCAKICAgVkFSQ0hBUigxNCkgcm9sZSAKICAgVkFSQ0hBUig4KSBzdGF0dXMgCiAgIElOVEVHRVIgdGVuYW50X2lkIAp9Cm5hcnJhdGl2ZXMgewogSU5URUdFUiBpZCBQSwogICBJTlRFR0VSIGNhc2VfaWQgCiAgIERBVEVUSU1FIGNyZWF0ZWRfYXQgCiAgIFRFWFQgZ2VuZXJhdGVkX3RleHQgCiAgIElOVEVHRVIgdGVuYW50X2lkIAogICBOVU1FUklDKDEwLF8yKSB0b3RhbF9mZWUgCiAgIE5VTUVSSUMoOCxfMikgdG90YWxfaG91cnMgCn0KcGFzc3dvcmRfcmVzZXRfdG9rZW5zIHsKIElOVEVHRVIgaWQgUEsKICAgREFURVRJTUUgZXhwaXJlc19hdCAKICAgSU5URUdFUiBpZGVudGl0eV9pZCAKICAgVkFSQ0hBUigyNTUpIHRva2VuX2hhc2ggCiAgIERBVEVUSU1FIHVzZWRfYXQgCn0Kc2V0dGluZ3MgewogSU5URUdFUiBpZCBQSwogICBWQVJDSEFSKDEwMCkga2V5IAogICBJTlRFR0VSIHRlbmFudF9pZCAKICAgVEVYVCB2YWx1ZSAKfQpzdWJzY3JpcHRpb25zIHsKIElOVEVHRVIgaWQgUEsKICAgQk9PTEVBTiBhY3RpdmUgCiAgIERBVEUgZW5kX2RhdGUgCiAgIFZBUkNIQVIoMTApIHBsYW4gCiAgIERBVEUgc3RhcnRfZGF0ZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KdGVuYW50cyB7CiBJTlRFR0VSIGlkIFBLCiAgIEJPT0xFQU4gYWN0aXZlIAogICBWQVJDSEFSKDUwMCkgbG9nb191cmwgCiAgIFZBUkNIQVIoMjU1KSBuYW1lIAogICBWQVJDSEFSKDcpIHByaW1hcnlfY29sb3IgCiAgIFZBUkNIQVIoNjMpIHN1YmRvbWFpbiAKfQp3b3JrX2xvZ3MgewogSU5URUdFUiBpZCBQSwogICBJTlRFR0VSIGNhc2VfaWQgCiAgIERBVEUgZGF0ZSAKICAgVkFSQ0hBUigxMDAwKSBkZXNjcmlwdGlvbiAKICAgTlVNRVJJQyg2LF8yKSBob3VycyAKICAgSU5URUdFUiBsYXd5ZXJfaWQgCiAgIFZBUkNIQVIoMTIpIHNvdXJjZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KdGVuYW50cyAxLS0wKyBhdWRpdF9sb2dzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIGF1ZGl0X2xvZ3MgOiBoYXMKdGVuYW50cyAxLS0wKyBjYXNlcyA6IGhhcwptZW1iZXJzaGlwcyAxLS0wKyBjYXNlX2Fzc2lnbm1lbnRzIDogaGFzCnRlbmFudHMgMS0tMCsgY2FzZV9hc3NpZ25tZW50cyA6IGhhcwpjYXNlcyAxLS0wKyBjYXNlX2Fzc2lnbm1lbnRzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIGRvY3VtZW50cyA6IGhhcwp0ZW5hbnRzIDEtLTArIGRvY3VtZW50cyA6IGhhcwpjYXNlcyAxLS0wKyBkb2N1bWVudHMgOiBoYXMKdGVuYW50cyAxLS0wKyBtZW1iZXJzaGlwcyA6IGhhcwppZGVudGl0aWVzIDEtLTArIG1lbWJlcnNoaXBzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIG1lbWJlcnNoaXBfaW52aXRlcyA6IGhhcwp0ZW5hbnRzIDEtLTArIG1lbWJlcnNoaXBfaW52aXRlcyA6IGhhcwpjYXNlcyAxLS0wKyBuYXJyYXRpdmVzIDogaGFzCnRlbmFudHMgMS0tMCsgbmFycmF0aXZlcyA6IGhhcwppZGVudGl0aWVzIDEtLTArIHBhc3N3b3JkX3Jlc2V0X3Rva2VucyA6IGhhcwp0ZW5hbnRzIDEtLTArIHNldHRpbmdzIDogaGFzCnRlbmFudHMgMS0tMCsgc3Vic2NyaXB0aW9ucyA6IGhhcwp0ZW5hbnRzIDEtLTArIHdvcmtfbG9ncyA6IGhhcwpjYXNlcyAxLS0wKyB3b3JrX2xvZ3MgOiBoYXMKbWVtYmVyc2hpcHMgMS0tMCsgd29ya19sb2dzIDogaGFzCg==)
