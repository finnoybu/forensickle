from PyInstaller.utils.hooks import collect_submodules, collect_data_files
hiddenimports = collect_submodules('gui')
datas = collect_data_files('gui', includes=['**/*.json'])
