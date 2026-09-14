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
memberships 1--0+ documents : has
cases 1--0+ documents : has
tenants 1--0+ documents : has
identities 1--0+ memberships : has
tenants 1--0+ memberships : has
tenants 1--0+ membership_invites : has
memberships 1--0+ membership_invites : has
tenants 1--0+ narratives : has
cases 1--0+ narratives : has
identities 1--0+ password_reset_tokens : has
tenants 1--0+ platform_audit_logs : has
identities 1--0+ platform_audit_logs : has
tenants 1--0+ settings : has
tenants 1--0+ subscriptions : has
memberships 1--0+ work_logs : has
tenants 1--0+ work_logs : has
cases 1--0+ work_logs : has


-->
![](https://mermaid.ink/img/LS0tCnRpdGxlOiBDYXNlciBFUkQKLS0tCmVyRGlhZ3JhbQphdWRpdF9sb2dzIHsKIElOVEVHRVIgaWQgUEsKICAgVkFSQ0hBUigxMDApIGFjdGlvbiAKICAgVkFSQ0hBUigyNTUpIHRhcmdldCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIERBVEVUSU1FIHRpbWVzdGFtcCAKICAgSU5URUdFUiB1c2VyX2lkIAp9CmNhc2VzIHsKIElOVEVHRVIgaWQgUEsKICAgREFURVRJTUUgY3JlYXRlZF9hdCAKICAgVkFSQ0hBUigxMSkgc3RhdHVzIAogICBJTlRFR0VSIHRlbmFudF9pZCAKICAgVkFSQ0hBUigyNTUpIHRpdGxlIAp9CmNhc2VfYXNzaWdubWVudHMgewogSU5URUdFUiBpZCBQSwogICBJTlRFR0VSIGNhc2VfaWQgCiAgIElOVEVHRVIgbWVtYmVyc2hpcF9pZCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KY2FzZV90YWdzIHsKIElOVEVHRVIgaWQgUEsKICAgSU5URUdFUiBjYXNlX2lkIAogICBWQVJDSEFSKDExKSBwcmFjdGljZV9hcmVhIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQpkb2N1bWVudHMgewogSU5URUdFUiBpZCBQSwogICBEQVRFVElNRSBhcmNoaXZlZF9hdCAKICAgSU5URUdFUiBjYXNlX2lkIAogICBWQVJDSEFSKDEwMCkgY29udGVudF90eXBlIAogICBEQVRFVElNRSBjcmVhdGVkX2F0IAogICBCSUdJTlQgZmlsZV9zaXplIAogICBWQVJDSEFSKDUwMCkgZmlsZV91cmwgCiAgIFZBUkNIQVIoOCkgZm9sZGVyX3R5cGUgCiAgIFZBUkNIQVIoMjU1KSBvcmlnaW5hbF9maWxlbmFtZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIElOVEVHRVIgdXBsb2FkZWRfYnkgCn0KaWRlbnRpdGllcyB7CiBJTlRFR0VSIGlkIFBLCiAgIFRFWFQgYmlvIAogICBWQVJDSEFSKDI1NSkgZW1haWwgCiAgIEJPT0xFQU4gaXNfc3VwZXJfYWRtaW4gCiAgIERBVEVUSU1FIGxhc3RfbG9naW5fYXQgCiAgIFZBUkNIQVIoMjU1KSBuYW1lIAogICBWQVJDSEFSKDI1NSkgcGFzc3dvcmRfaGFzaCAKICAgVkFSQ0hBUig1MDApIHBob3RvX3VybCAKICAgSU5URUdFUiB0b2tlbl92ZXJzaW9uIAogICBJTlRFR0VSIHllYXJzX29mX2V4cGVyaWVuY2UgCn0KbWVtYmVyc2hpcHMgewogSU5URUdFUiBpZCBQSwogICBCT09MRUFOIGFjdGl2ZSAKICAgTlVNRVJJQyg4LF8yKSBob3VybHlfcmF0ZSAKICAgSU5URUdFUiBpZGVudGl0eV9pZCAKICAgVkFSQ0hBUigxNCkgcm9sZSAKICAgQk9PTEVBTiBzaG93X29uX3B1YmxpY19wYWdlIAogICBJTlRFR0VSIHRlbmFudF9pZCAKfQptZW1iZXJzaGlwX2ludml0ZXMgewogSU5URUdFUiBpZCBQSwogICBEQVRFVElNRSBjcmVhdGVkX2F0IAogICBWQVJDSEFSKDI1NSkgZW1haWwgCiAgIElOVEVHRVIgaW52aXRlZF9ieSAKICAgREFURVRJTUUgcmVzcG9uZGVkX2F0IAogICBWQVJDSEFSKDE0KSByb2xlIAogICBWQVJDSEFSKDgpIHN0YXR1cyAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KbmFycmF0aXZlcyB7CiBJTlRFR0VSIGlkIFBLCiAgIElOVEVHRVIgY2FzZV9pZCAKICAgREFURVRJTUUgY3JlYXRlZF9hdCAKICAgVEVYVCBnZW5lcmF0ZWRfdGV4dCAKICAgVkFSQ0hBUigyKSBsYW5ndWFnZSAKICAgREFURSBwZXJpb2RfZW5kIAogICBEQVRFIHBlcmlvZF9zdGFydCAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCiAgIE5VTUVSSUMoMTAsXzIpIHRvdGFsX2ZlZSAKICAgTlVNRVJJQyg4LF8yKSB0b3RhbF9ob3VycyAKfQpwYXNzd29yZF9yZXNldF90b2tlbnMgewogSU5URUdFUiBpZCBQSwogICBEQVRFVElNRSBleHBpcmVzX2F0IAogICBJTlRFR0VSIGlkZW50aXR5X2lkIAogICBWQVJDSEFSKDI1NSkgdG9rZW5faGFzaCAKICAgREFURVRJTUUgdXNlZF9hdCAKfQpwbGF0Zm9ybV9hdWRpdF9sb2dzIHsKIElOVEVHRVIgaWQgUEsKICAgVkFSQ0hBUigxMDApIGFjdGlvbiAKICAgSU5URUdFUiBpZGVudGl0eV9pZCAKICAgSU5URUdFUiB0YXJnZXRfdGVuYW50X2lkIAogICBEQVRFVElNRSB0aW1lc3RhbXAgCn0Kc2V0dGluZ3MgewogSU5URUdFUiBpZCBQSwogICBWQVJDSEFSKDEwMCkga2V5IAogICBJTlRFR0VSIHRlbmFudF9pZCAKICAgVEVYVCB2YWx1ZSAKfQpzdWJzY3JpcHRpb25zIHsKIElOVEVHRVIgaWQgUEsKICAgQk9PTEVBTiBhY3RpdmUgCiAgIERBVEUgZW5kX2RhdGUgCiAgIFZBUkNIQVIoMTApIHBsYW4gCiAgIERBVEUgc3RhcnRfZGF0ZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KdGVuYW50cyB7CiBJTlRFR0VSIGlkIFBLCiAgIEJPT0xFQU4gYWN0aXZlIAogICBEQVRFVElNRSBjcmVhdGVkX2F0IAogICBWQVJDSEFSKDUwMCkgbG9nb191cmwgCiAgIFZBUkNIQVIoMjU1KSBuYW1lIAogICBWQVJDSEFSKDcpIHByaW1hcnlfY29sb3IgCiAgIFZBUkNIQVIoNjMpIHN1YmRvbWFpbiAKfQp3b3JrX2xvZ3MgewogSU5URUdFUiBpZCBQSwogICBJTlRFR0VSIGNhc2VfaWQgCiAgIERBVEUgZGF0ZSAKICAgVkFSQ0hBUigxMDAwKSBkZXNjcmlwdGlvbiAKICAgTlVNRVJJQyg2LF8yKSBob3VycyAKICAgSU5URUdFUiBsYXd5ZXJfaWQgCiAgIFZBUkNIQVIoMTIpIHNvdXJjZSAKICAgSU5URUdFUiB0ZW5hbnRfaWQgCn0KdGVuYW50cyAxLS0wKyBhdWRpdF9sb2dzIDogaGFzCm1lbWJlcnNoaXBzIDEtLTArIGF1ZGl0X2xvZ3MgOiBoYXMKdGVuYW50cyAxLS0wKyBjYXNlcyA6IGhhcwptZW1iZXJzaGlwcyAxLS0wKyBjYXNlX2Fzc2lnbm1lbnRzIDogaGFzCmNhc2VzIDEtLTArIGNhc2VfYXNzaWdubWVudHMgOiBoYXMKdGVuYW50cyAxLS0wKyBjYXNlX2Fzc2lnbm1lbnRzIDogaGFzCnRlbmFudHMgMS0tMCsgY2FzZV90YWdzIDogaGFzCmNhc2VzIDEtLTArIGNhc2VfdGFncyA6IGhhcwptZW1iZXJzaGlwcyAxLS0wKyBkb2N1bWVudHMgOiBoYXMKY2FzZXMgMS0tMCsgZG9jdW1lbnRzIDogaGFzCnRlbmFudHMgMS0tMCsgZG9jdW1lbnRzIDogaGFzCmlkZW50aXRpZXMgMS0tMCsgbWVtYmVyc2hpcHMgOiBoYXMKdGVuYW50cyAxLS0wKyBtZW1iZXJzaGlwcyA6IGhhcwp0ZW5hbnRzIDEtLTArIG1lbWJlcnNoaXBfaW52aXRlcyA6IGhhcwptZW1iZXJzaGlwcyAxLS0wKyBtZW1iZXJzaGlwX2ludml0ZXMgOiBoYXMKdGVuYW50cyAxLS0wKyBuYXJyYXRpdmVzIDogaGFzCmNhc2VzIDEtLTArIG5hcnJhdGl2ZXMgOiBoYXMKaWRlbnRpdGllcyAxLS0wKyBwYXNzd29yZF9yZXNldF90b2tlbnMgOiBoYXMKdGVuYW50cyAxLS0wKyBwbGF0Zm9ybV9hdWRpdF9sb2dzIDogaGFzCmlkZW50aXRpZXMgMS0tMCsgcGxhdGZvcm1fYXVkaXRfbG9ncyA6IGhhcwp0ZW5hbnRzIDEtLTArIHNldHRpbmdzIDogaGFzCnRlbmFudHMgMS0tMCsgc3Vic2NyaXB0aW9ucyA6IGhhcwptZW1iZXJzaGlwcyAxLS0wKyB3b3JrX2xvZ3MgOiBoYXMKdGVuYW50cyAxLS0wKyB3b3JrX2xvZ3MgOiBoYXMKY2FzZXMgMS0tMCsgd29ya19sb2dzIDogaGFzCg==)
