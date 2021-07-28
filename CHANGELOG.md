# Changelog

<!--next-version-placeholder-->

## v0.7.0 (2021-07-28)
### Feature
* Add stream.alternative(bool) ([`3adef70`](https://github.com/vberlier/tokenstream/commit/3adef707670c8a1cb00cca3c3d5174c1db4f0d0b))

## v0.6.2 (2021-07-23)
### Fix
* Don't capture newlines in whitespace tokens ([`d17783e`](https://github.com/vberlier/tokenstream/commit/d17783eb3f13ce4eb5c18ee36eb3bc92434f10a9))

## v0.6.1 (2021-07-22)
### Fix
* Handle pattern explanation with no pattern ([`1de098b`](https://github.com/vberlier/tokenstream/commit/1de098b069315cb56670739238f133020fd5fd3c))

## v0.6.0 (2021-07-22)
### Feature
* Add arbitrary user data ([`105553f`](https://github.com/vberlier/tokenstream/commit/105553f073a03ccee25eb2330f6d69459279802b))

## v0.5.0 (2021-06-24)
### Feature
* Add alternative method and choose method ([`0794172`](https://github.com/vberlier/tokenstream/commit/0794172e558722bceb3353af609562520185967c))

### Fix
* Swallow syntax errors when checkpoint is not committed yet ([`54e77ef`](https://github.com/vberlier/tokenstream/commit/54e77ef25033cd0a19ec7d716deb855ac389d0d7))
* Don't raise UnexpectedEOF if peek_until without patterns ([`bcee95a`](https://github.com/vberlier/tokenstream/commit/bcee95af5d25344f29f9de43c3b6ed2c7d1e2c27))

## v0.4.1 (2021-06-17)
### Fix
* Typo ([`934f52c`](https://github.com/vberlier/tokenstream/commit/934f52c1d5c513b208ac669249f2a454ab8cd68e))

## v0.4.0 (2021-06-17)
### Feature
* Add collect_any and docs ([`2d35ba3`](https://github.com/vberlier/tokenstream/commit/2d35ba35ce889002d3d8f205e9a9dd1ae7b78618))

### Fix
* Take into account indentation_skip ([`cbfe3e3`](https://github.com/vberlier/tokenstream/commit/cbfe3e3c5f98b91346544cfe9af0e9dcff595343))

## v0.3.0 (2021-06-16)
### Feature
* Add stream checkpoint ([`8ad92bf`](https://github.com/vberlier/tokenstream/commit/8ad92bfeea17fb5b5d6abbb518df6f43c5209b61))

### Fix
* Accurate end_colno when the token contains newlines ([`3cdb432`](https://github.com/vberlier/tokenstream/commit/3cdb432999cf6e1fe3224e1507c9d61ca73ce6c7))
* Collect with no patterns properly defers to the main iterator ([`3c6000a`](https://github.com/vberlier/tokenstream/commit/3c6000a3f326fa555b05842adb8752ea4acc3144))

### Documentation
* Update README ([`4739d83`](https://github.com/vberlier/tokenstream/commit/4739d8389b25752eba91ef39761e52a93a96c455))

## v0.2.0 (2021-06-14)
### Feature
* Add stream.peek_until ([`8b0475c`](https://github.com/vberlier/tokenstream/commit/8b0475c3a4670d63202eb144e0b2b86c1b187bac))
* Add token stream ([`02bdabd`](https://github.com/vberlier/tokenstream/commit/02bdabdc942a0a85db1d38f0c94fcbd4cf441745))

### Fix
* Add getting started ([`1907b06`](https://github.com/vberlier/tokenstream/commit/1907b0640405d56f67377602b5d834ada3af8c28))

### Documentation
* Update README ([`d9fb1dc`](https://github.com/vberlier/tokenstream/commit/d9fb1dc85eee48755ee7448a9c1051daedad256d))
* Add s-expression example ([`bb2b503`](https://github.com/vberlier/tokenstream/commit/bb2b50367f5d55b5092f3dd869e9d417661e1ea0))
