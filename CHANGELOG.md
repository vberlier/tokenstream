# Changelog

<!--next-version-placeholder-->

## v1.3.2 (2022-02-19)
### Fix
* Update docs ([`a788ff1`](https://github.com/vberlier/tokenstream/commit/a788ff194eb630555a01ba9837a160e40f97dbec))

## v1.3.1 (2021-12-06)
### Fix
* Sort expected patterns in explanation ([`c1c26cb`](https://github.com/vberlier/tokenstream/commit/c1c26cb874229a5e0319c882f3b6e5567fd14870))

## v1.3.0 (2021-12-01)
### Feature
* Make it possible to copy the stream ([`5a4a41c`](https://github.com/vberlier/tokenstream/commit/5a4a41c8f4a137a9c98bdda856cf4a4ba2169d0b))

## v1.2.7 (2021-11-30)
### Fix
* Get() method was returning a list instead of a single token ([`accf784`](https://github.com/vberlier/tokenstream/commit/accf7843f1263dbba6aa0893a157be608ed1758a))

## v1.2.6 (2021-11-25)
### Fix
* Prevent duplicating expected patterns ([`10cec04`](https://github.com/vberlier/tokenstream/commit/10cec045e3658333cf9a381fd166bcb8cf1a3064))

## v1.2.5 (2021-11-25)
### Fix
* Simplify expected_patterns merging ([`ad10e50`](https://github.com/vberlier/tokenstream/commit/ad10e50804770a11c530a8234aeadd6b9561fb0f))

## v1.2.4 (2021-11-25)
### Fix
* Properly prioritize errors that occur later in the stream ([`a665924`](https://github.com/vberlier/tokenstream/commit/a665924a68e43a6f0f7b1b8cc069761b32436323))

## v1.2.3 (2021-10-20)
### Fix
* Set invalid syntax location for unexpected token ([`4231809`](https://github.com/vberlier/tokenstream/commit/423180921e036bdfb0ea3c1025841248aedbb010))

## v1.2.2 (2021-10-09)
### Fix
* Handle windows line endings ([`068144d`](https://github.com/vberlier/tokenstream/commit/068144d0cadad0265ae292ec5dd9a925265735ef))

## v1.2.1 (2021-09-24)
### Fix
* With_horizontal_offset doesn't modify unkown location anymore ([`e17f897`](https://github.com/vberlier/tokenstream/commit/e17f897fec2feb53b0df3c7c62efdb0fe6c1fcd1))

## v1.2.0 (2021-09-19)
### Feature
* Make it possible to know if a checkpoint was rolled back ([`0765e96`](https://github.com/vberlier/tokenstream/commit/0765e96aec93bcc6b0a60956ac509afd4f63e1c6))

## v1.1.0 (2021-09-16)
### Feature
* Add stream.reset() ([`1af0d47`](https://github.com/vberlier/tokenstream/commit/1af0d47b93082ae374ca8edef8f03f8a549e1fdb))

### Fix
* Do not register the first alternative exception twice ([`1bb7102`](https://github.com/vberlier/tokenstream/commit/1bb71027bdf126ae5c439c149b34a99eeb5973fd))

## v1.0.5 (2021-09-15)
### Fix
* Make it possible to use None to disable previous rules ([`66e468a`](https://github.com/vberlier/tokenstream/commit/66e468ad068a3b1c9c34f0e72b63df38b7710a81))

## v1.0.4 (2021-09-14)
### Fix
* Add period to all error messages ([`c1c32b0`](https://github.com/vberlier/tokenstream/commit/c1c32b02732b66ac4080585f1360bfc429c7f0e2))

## v1.0.3 (2021-09-14)
### Fix
* Don't show token value if it's empty ([`6337bfd`](https://github.com/vberlier/tokenstream/commit/6337bfd35f0f51996cfae15174fe4f1b1428b7f2))

## v1.0.2 (2021-09-14)
### Fix
* Don't detect indent when the line is blank ([`175e02e`](https://github.com/vberlier/tokenstream/commit/175e02eadb75d027199f268edbede774632ab34c))
* Properly handle full dedent ([`04b9dab`](https://github.com/vberlier/tokenstream/commit/04b9dab09bf32cb368a60a009650689e7cf24145))
* Add eof and invalid tokens ([`264a398`](https://github.com/vberlier/tokenstream/commit/264a398ad4e55e89e0bfb503db2af98b38492d00))

## v1.0.1 (2021-09-08)
### Fix
* Handle non SourceLocation end_location in set_location ([`f16b378`](https://github.com/vberlier/tokenstream/commit/f16b378fbdc52942bcf14a8d4b41d34158d867d7))

## v1.0.0 (2021-09-08)
### Feature
* Move SourceLocation into its own module ([`95aabae`](https://github.com/vberlier/tokenstream/commit/95aabae6058bb3c13bbd4f15a372d480f94a22b2))

### Breaking
* remove InvalidSyntax.set_location in favor of the general-purpose setlocation function  ([`95aabae`](https://github.com/vberlier/tokenstream/commit/95aabae6058bb3c13bbd4f15a372d480f94a22b2))

## v0.7.5 (2021-09-04)
### Fix
* Combine unexpected token patterns when using the choose() method ([`b8665e8`](https://github.com/vberlier/tokenstream/commit/b8665e8b10e451467e2dae1659e9c999213aa348))

## v0.7.4 (2021-08-30)
### Fix
* Tweak pattern explanation when there are a lot of token types ([`0a9e007`](https://github.com/vberlier/tokenstream/commit/0a9e007ea77095e040f87c9c0c61539b3245e7a1))

## v0.7.3 (2021-08-30)
### Fix
* Properly restore previous regex when syntax changes ([`aeae860`](https://github.com/vberlier/tokenstream/commit/aeae860707149ec6bd1e2d730dd613cf097c231d))

## v0.7.2 (2021-08-29)
### Fix
* Raise IndexError for negative indices for current and previous tokens ([`7b5010b`](https://github.com/vberlier/tokenstream/commit/7b5010bfb801ee1e72d1a16a039aa2ff9ab7d1b9))

## v0.7.1 (2021-08-28)
### Fix
* Make it possible to emit errors from tokens ([`b97ab2d`](https://github.com/vberlier/tokenstream/commit/b97ab2d4913c2f0410251ab0cbb817f5082a61df))

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
