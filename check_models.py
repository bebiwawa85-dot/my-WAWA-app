from together import Together
client = Together(api_key="5cf3f4d760983464420305abfb35dd322be02f47bf5e86ac95910ceebc58712e")
models = client.models.list()
for m in models:
    print(m)
