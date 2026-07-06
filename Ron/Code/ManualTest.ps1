
$file_name = if ($args.Count -gt 0) { $args[0] } else { "." }

#python $file_name

python $file_name; python 	 -m unittest $file_name; python -s -m pytest $file_name; black $file_name; flake8 $file_name


#if ($LASTEXITCODE -eq 0) { python -m unittest discover tests}
#if ($LASTEXITCODE -eq 0) { python -m pytest tests}
#if ($LASTEXITCODE -eq 0) { black --check $file_name }
#if ($LASTEXITCODE -eq 0) { flake8 $file_name }
