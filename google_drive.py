from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
gauth.LocalWebserverAuth()

#  вспомогательная функция
def create_folder(folder_id, folderName, drive):
    file_metadata = {
        'title': folderName,
        'parents': [{'id': folder_id}],  # parent folder
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive.CreateFile(file_metadata)
    folder.Upload()


#  создаем папку под названием folderName в директории с folder_id
def create_folder_in_folder(root_folder, new_folder):
    drive = GoogleDrive(gauth)
    folders = drive.ListFile(
        {
            'q': "title='" + root_folder + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder:
            create_folder(folder['id'], new_folder, drive)


def upload_file(file, input_directory, out_path):
    try:
        drive = GoogleDrive(gauth)
        my_file = drive.CreateFile({'title': f'{out_path}/{file}'})  # создаем файл на диске
        my_file.SetContentFile(f'{input_directory}/{file}')  # присваиваем выгружаемому файлу значение нашего файла
        my_file.Upload()

    except Exception as _ex:
        return 'Error in file upload'


def is_directory_or_file_exists(root_folder, check_folder_or_file):
    drive = GoogleDrive(gauth)

    root_folder_id = ''
    folders = drive.ListFile(
        {
            'q': "title='" + root_folder + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder:
            root_folder_id = folder['id']

    folders = drive.ListFile({'q': "\'" + root_folder_id + "\'" + " in parents and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == check_folder_or_file:
            my_file = drive.CreateFile({'parents': [{'id': fileID}]})  # создаем файл на диске
    return False


def upload_file_2(root_folder, check_folder_or_file):
    drive = GoogleDrive(gauth)

    root_folder_id = ''
    folders = drive.ListFile(
        {
            'q': "title='" + root_folder + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder:
            root_folder_id = folder['id']

    folders = drive.ListFile({'q': "\'" + root_folder_id + "\'" + " in parents and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == check_folder_or_file:
            return True
    return False


# create_folder('root', 'cat2', GoogleDrive(gauth))
# create_folder_in_folder('1', '6')
upload_file('mish.png', 'files/497684582', 'files/497684582')
# is_directory_or_file_exists('files', 'mdDinRxBMko.jpg')

