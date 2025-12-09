from django.test import TestCase

# Create your tests here.

# Push sales price, master data, and gls stock list to weclapp
# Push sales price and other data to shopware 6
# Push sales price and product data to aera
# Push sales price to wawibox
# Push sales price to dentalheld
# send price promotions to weclapp


# get orders from aera and save to an aera model
# get orders from wawibox and save to a wawibox model
# get orders from dentalheld and save to a dentalheld model

# send aera orders to weclapp
# send wawibox orders to weclapp
# send dentalheld orders to weclapp
# get weclapp orders ready for dropshipping
# send weclapp orders to gls
# get gls order delivery feedback
# send order delivery feedback to weclapp


# create a product model on core
# fetch all aera products and create or update instances of the core product
# fetch all wawibox products and create or update instances of the core product
# fetch all shopware 6 products and create or update instances of the core product
# fetch all dentalheld products and create or update instances of the core product

# or if everything is on weclapp, fetch all and update the core product
# when updated,
# sync core product to fk fields on aera competitor price
# sync core product to fk fields on GLSMasterData
# sync core product to fk fields on GLS AdditionalProduct
# sync core product to fk fields on GLS BlockedProduct
# sync core product to fk fields on GLSPriceList
# sync core product to fk fields on GLSPromotionPosition
# sync core product to fk fields on GLSPromotionPrice
# sync core product to fk fields on wawibox competitor price
