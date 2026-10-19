 # Check current source f push/pull
 give remote -v
 # Set source to HTT based method
 git remote set-url origin https://github.com/PNWSkyHippy/Trading_Bot_V2
 # Set source to SSH based method
 git remote set-url origin git@github.com:PNWSkyHippy/Trading_Bot_V2.git
 
# To safely sync your disjointed local and remote repositories without deleting any unique 
# files or newer changes on either side, use a combination of fetch, merge/rebase with 
# non-destructive strategies, and careful pushing.

# Commit any uncommitted changes you have on your local machine so Git tracks them properly:
git add .
git commit -m "Save local changes before sync"

# Fetch the latest remote state without altering local filesDownload all remote branch data without automatically changing your working files:
git fetch origin

# Merge remote changes into local safely
git merge origin/main --no-commit --no-ff
# If there are problems
# to pull up the list of conflicts
git status --short | rg -i  '^UU'

# To keep the local copy of conflicts 
git checkout --ours Html-Files/side-panels.jsx
git add Html-Files/side-panels.jsx

# To take the repos newer versions
git checkout --theirs Ron/Code/DictionaryListsReference.py
git add Ron/Code/DictionaryListsReference.py

# once you have resolved the blocks or chosen the correct version
git add .
git commit -m "Merge remote main keeping newer edits"
git push origin main


# if everything merges cleanly, complete the commit:
git commit -m "Merge remote branch safely"

# Push combined changes back to the remote repositorySend your unified history back to the 
# remote server:

git push origin main

# Reset afer unwanted files comited causig errors
git reset --mixed origin/main
git rm -r --cached .
git add .
git commit -m "chore: wipe binary bloat and add fresh files"
git push origin main
