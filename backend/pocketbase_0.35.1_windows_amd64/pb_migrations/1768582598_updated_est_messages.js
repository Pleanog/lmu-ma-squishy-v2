/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_387303225")

  // update collection data
  unmarshal({
    "name": "test_messages"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_387303225")

  // update collection data
  unmarshal({
    "name": "est_messages"
  }, collection)

  return app.save(collection)
})
