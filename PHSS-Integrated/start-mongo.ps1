# Start MongoDB Community Server from D:\mongodb with data stored on D: drive
Write-Host "Starting MongoDB on 127.0.0.1:27017 (data stored in D:\mongodb\data)..." -ForegroundColor Cyan
& "D:\mongodb\bin\mongod.exe" --dbpath "D:\mongodb\data" --bind_ip 127.0.0.1 --port 27017
