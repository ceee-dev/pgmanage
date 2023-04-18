# PgManage
We proudly leverage all of the great work Open Source work done by the original
(now dormant) project https://github.com/OmniDB/OmniDB 


**Website & Downloads**: https://github.com/commandprompt/pgmanage

**Full Documentation**: https://pgmanage.readthedocs.io/en/latest/

# Run it yourself from source
If you want or need a new feature, submit a pull request for us to consider.

## Pre-req's for Debian/Ubuntu
```
sudo apt install python3-dev python3-venv python3-wheel libpq-dev libldap2-dev libsasl2-dev
```

## Pre-req's for Enterprise Linux flavors
```
sudo yum install xxx yyy zzz
```

## Pre-req's for OSX using Homebrew
```
brew install python3 xxx yyy zzz
```

## Build instructions
```
git clone https://github.com/commandprompt/pgmanage
cd pgmanage
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.8.10 --skip-existing
pyenv local 3.8.10
poetry env use 3.8
poetry install --with dev
poetry shell
```

## Start it up
```
cd pgmanage/pgmanage
python3 pgmanage-server.py
```

# PgManage 1.0 Beta

## Release Date: Apr 20 2023

## Release Notes

- New features:
  - added backup/restore support for Postgres  
  - first version of PgManage Handbook was published to https://pgmanage.readthedocs.io/en/latest

- Major Bugs fixed:
  - fixed .AppImage compatibility issues for newer Linux distributions which do not have libcrypt installed
  - added logic to terminate stale back-end process if the front-end process crashes
  - fixed application UI process memory leaks
  

- UI/UX Improvements:
  - improved support for configuration options search in Postgres Server Configuration Management
  - automatically readjust query editor font size when the application font size changes
  - various application layout and UI improvements
  - limited minimum application window size to 1024x766
  - fixed splash screen flickering/position issues during the application startup
  - add PgManage Handbook links to application error modal dialogs
  - improved handling of drag-and-drop reordering for database operations tabs
  
- Other changes
  - added support for configurable Postgresql Client binary path in application settings
  - excluded SASS libraries and .sass files from the release builds
  - include EGL/GLES libraries into app release builds
  - pev2 upgraded to v1.7.0
  - removed "plugins" and other obsolete menu items from the application UI
  - removed unused files and dead code from the project
  - shred SSH keys stored in the app during the Master Password Reset

# PgManage 1.0 Alpha

## Release Date: Feb 21 2023

## Release Notes

- New features:
  - new connection management UI
  - added support for postgres server configuration management
  - new explain/analyze UI powered by pev2, including pev2 dark theme support
  - connection credential encryption
  - backported support for monitoring data-grid-based monitoring widgets
  - backported pie charts widgets for numbackends and database sizes
  - added password strength validation for user and master passwords
  - PostgreSQL 9.6, 10, 11, 12, 13, 14 and 15 support

- Major Bugs fixed:
  - fixed data export to csv/xls format in the desktop version of the app
  - added superuser permission check on all user management APIs
  - extra validations added to prevent creation of unnamed connection groups
  - fixed external links not working in the desktop variant of the app
  - fixed postgres special commands on postgresql versions 12 and higher
  - fixed broken postgres documentation links available in database tree view menus
  - made all web/cdn app dependencies local so pgmanage can work properly without an internet connection

- UI/UX Improvements:
  - reorganized connection management menus in the left menu bar 
  - fixed DDL tab auto resizing
  - the top-right utilities menu now expands on click instead of mouse-hover
  - added DDL/properties tab resize limits to prevent it from becoming impossible to grab/resize back
  - unified tooltip appearance throughout the whole app
  - unified pictogram look and feel thoughout the whole app
  - improved database tree view navigation by adding smooth scroll to the newly expanded tree node. previously when some tree view node was expanded it jumped out of sight
  - improved data grid/table readability
  - improved database entity tree view readability
  - fixed date formatting in sql command history grid
  - fixed date formatting in db console command history grid
  - proper styling for dialog primary and secondary buttons. the secondary buttons in forms and dialogs were previously looked disable/grayed-out which was confusing.
  - the autocommit checkbox on query tab now stays visible despite of application window size
removed the option to make connections public in desktop variant of the app (which has only one user so shared/public connections make no sense)

- Other changes
  - added postgresql 14 and 15  support
  - application data directory and db/log file naming was changed from omnidb* to pgmanage*.

![](https://pgmanage.readthedocs.io/en/latest/_images/intro.png)
