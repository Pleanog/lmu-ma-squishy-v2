/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_2605467279")

  // update field
  collection.fields.addAt(5, new Field({
    "hidden": false,
    "id": "file410859157",
    "maxSelect": 99,
    "maxSize": 0,
    "mimeTypes": [
      "audio/mpeg",
      "audio/ogg",
      "audio/flac",
      "audio/midi",
      "audio/ape",
      "audio/musepack",
      "audio/amr",
      "audio/wav",
      "audio/aiff",
      "audio/basic",
      "audio/mp4",
      "audio/x-m4a",
      "audio/aac",
      "audio/x-unknown",
      "audio/qcelp"
    ],
    "name": "audio",
    "presentable": false,
    "protected": false,
    "required": false,
    "system": false,
    "thumbs": [],
    "type": "file"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_2605467279")

  // update field
  collection.fields.addAt(5, new Field({
    "hidden": false,
    "id": "file410859157",
    "maxSelect": 99,
    "maxSize": 0,
    "mimeTypes": [],
    "name": "audio",
    "presentable": false,
    "protected": false,
    "required": false,
    "system": false,
    "thumbs": [],
    "type": "file"
  }))

  return app.save(collection)
})
