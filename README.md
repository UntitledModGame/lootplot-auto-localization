Auto translate UMG mod strings using DeepL

Run example (run `python -m umg_autolocalize --help` for complete command-line options), newlines added for readability:

```
python
-m umg_autolocalize
--apikey <DeepL_key>
--output output/directory
--free
--target-lang ID
lootplot/saves/save1/localization/localization.json
lootplot/clientdata/localization/localization.json
```

If you're using DeepL Pro, remove the `--free` command-line option.
