from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from azure.identity import DefaultAzureCredential #needed for auth as AAD App - currently not in use
from azure.identity import InteractiveBrowserCredential
from azure.storage.blob import BlobServiceClient
from azure.mgmt.media import AzureMediaServices
from azure.mgmt.media.models import Asset
import os
from azure.mgmt.media.models import (
  Transform,
  Filters,
  Rotation,
  TransformOutput,
  StandardEncoderPreset,
  H264Layer,
  AacAudio,
  H264Video,
  H264Complexity,
  Mp4Format,
  AacAudioProfile,
  OnErrorType,
  Priority,
  H265Video,
  H265Layer,
  ContentKeyPolicy, #contentPolicy$ needed to create kontent key policy
  ContentKeyPolicyOption, 
  ContentKeyPolicyPlayReadyConfiguration, #would be needed if streaming policy =! open
  ContentKeyPolicyPlayReadyLicense, 
  ContentKeyPolicyPlayReadyLicenseType,
  ContentKeyPolicyPlayReadyContentEncryptionKeyFromHeader,
  ContentKeyPolicyPlayReadyContentType,
  ContentKeyPolicyClearKeyConfiguration,
  ContentKeyPolicyOpenRestriction,
  StreamingLocator,
  Job,
  StreamingEndpoint,
  )
import asyncio
from datetime import timedelta
import random


os.environ["AZURE_TENANT_ID"] = ""
os.environ["AZURE_CLIENT_ID"] = ""
#os.environ["AZURE_CLIENT_SECRET"] = "xxx" #AAD App
os.environ["AZURE_TENANT_DOMAIN"] = "stud.fra-uas.de"
os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"] = ""
os.environ["AZURE_RESOURCE_GROUP"] = ""
os.environ["AZURE_SUBSCRIPTION_ID"]= ""
os.environ["AZURE_ARM_TOKEN_AUDIENCE"] = "https://management.core.windows.net"
os.environ["AZURE_ARM_ENDPOINT"] = "https://management.azure.com/"
		
def signin():
	# Erstelle ein Credentialobjekt, um gegen Azure zu Authentifizieren
	print("Funktion Singin aufgerufen")
	global blob_service_client
	global token_credential
	global client
	token_credential = InteractiveBrowserCredential()
	client = AzureMediaServices(token_credential, os.environ["AZURE_SUBSCRIPTION_ID"], logging_enable=True)
	print (str(token_credential))
	blob_service_client = BlobServiceClient(
        account_url="https://storagebaolejnicki.blob.core.windows.net",
        credential=token_credential)
	


def select_data():
	# Öffnet ein Dialogfenster, um eine Datei auszuwählen. Diese wird im weiteren Verlauf in den Azure Storage geladen.
	global abs_path
	global filename
	name=filedialog.askopenfile()
	print(name) #debug
	if name:
		abs_path = os.path.abspath(name.name) #speichere den absoluten Pfad der ausgewähten Datei in Variable
		filename = os.path.basename(abs_path)
		print ("Pfad der Datei: " + str(abs_path)) #debug
		print("Dateiname: " + filename) #debug
		Label(frm, text ="Die Datei zum Upload befindet sich unter : " + "\n" +  str(abs_path)).grid(column = 0, row = 6) #dieses Label steht in der GUI.
	return abs_path


def show_container(blob_service_client: BlobServiceClient):
	#Listet alle Container des Speicherkontos auf und erstellt pro Container einen Radiobutton.
	global my_container
	all_containers = blob_service_client.list_containers(include_metadata=False)
	n=0
	my_container = tk.StringVar()
	for container in all_containers:
		n=n+1
		button = tk.Radiobutton(frm, text=container['name'], value=container['name'], variable=my_container ,tristatevalue=0, command = lambda : print(my_container.get())).grid(column=2, row=n+1)
		print(container)

def create_container(): #Erstellt einen neuen Container im Speicherkonto, "blob_service_client" übergibt die passende URL.
	global container_name
	# Namen aus dem Formular holen und Container erstellen
	print(container_name.get())#kann noch weg
	container_client = blob_service_client.create_container(container_name.get())

def upload_data():
	#Lädt die Datei aus select_data() als Blob in den Container, welcher mit einem der Radiobuttons ausgewählt wurde.
	blob_client = blob_service_client.get_blob_client(container=my_container.get(), blob=filename)

	print("\nDie folgende Datei wird als blob in den Azure Speicher hochgeladen: " + filename)

	print("Containername: " + str(my_container.get())) #debug
	print("Blobname: " + filename) #debug
	#Erstellt ein Asset (Medienobjekt) und lässt es auf den vorher hochgeladenen Blob zeigen. Nötig, weil ein Blob erstmal nur Daten beinhaltet, Media Services kann nur mit Assets, nicht Blobs arbeiten. Assets werden jedoch in Blobs gespeichert.
	new_asset = Asset(alternate_id="erstellt mit Upload_data()", description="hier könnte eine Beschreibung stehen", container=my_container.get())
	asset = client.assets.create_or_update(resource_group_name=os.environ["AZURE_RESOURCE_GROUP"], account_name=os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"], asset_name=filename, parameters=new_asset)
	with open(file=abs_path, mode="rb") as data:
		blob_client.upload_blob(data)

def show_blobs(blob_service_client):
	global my_blob
	my_blob = tk.StringVar()
	n=0
	"""
	#listet alle Blobs eines Containers auf. Anhängig vom ausgewählten Container.
	container_client = blob_service_client.get_container_client(container=my_container.get())
	blob_list = container_client.list_blobs()
	for blob in blob_list:
		n=n+1
		button = tk.Radiobutton(frm, text=blob.name, value=blob.name, variable=my_blob ,tristatevalue=0, command = lambda : print("gewählter blob: " + my_blob.get())).grid(column=5, row=n+1)
	"""
	#listet alle Assets des Mediaservices auf. Unabhängig vom ausgewählten Container.
	for asset in client.assets.list(resource_group_name=os.environ["AZURE_RESOURCE_GROUP"], account_name=os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"]):
		n=n+1
		button = tk.Radiobutton(frm, text=asset.name, value=asset.name, variable=my_blob ,tristatevalue=0, command = lambda : print("gewähltes Asset: " + my_blob.get())).grid(column=3, row=n+1)
		print(asset.name)

async def create_transform():
	#Erstellt die Transformation. Enthält Informationen zum Video- und Audioencoding
	client = AzureMediaServices(token_credential, os.environ["AZURE_SUBSCRIPTION_ID"], logging_enable=True)
	uniqueness = str(random.randint(0,99999)) #um Namenskonflikten vorzubeugen
	name_prefix = "encoded" #wird für die Ausgabedatei verwendet

	transform_name = "stdencoding"
	print("Beginne mit der Erstellung des Transfomations-Templates: " + transform_name) #debug
	
	transform_output = TransformOutput(
		preset = StandardEncoderPreset(
		codecs = [AacAudio(channels=2, sampling_rate=48000, bitrate=128000, profile=AacAudioProfile.AAC_LC),
	    H264Video(key_frame_interval=timedelta(seconds=2), complexity=H264Complexity.BALANCED, layers=[H264Layer(bitrate=3600000, width="1280", height="720", label="HD-3600kbps")])],
		# Spezifieziert das Format des Ausgabevideos - einmal Video und Audio, ein weiteres für das Thumbnail Bild
		formats = [Mp4Format(filename_pattern="Video-{Basename}-{Label}-{Bitrate}{Extension}")],
		),
		# falls ein Fehler auftritt, wird hier bestimmt, wie Azure weiter verfahren soll. (job wird abgebrochen und nicht weiter bearbeitet)
		on_error=OnErrorType.STOP_PROCESSING_JOB,
		# Die Priorität des Jobs (relativ zu anderen evtl konkurrierenden Aufträgen). Mögliche Werte sind Normal, high oder low
		relative_priority=Priority.NORMAL
		)
	print("Transformation zur Encodierung wird erstellt...")

    # hier wreden der Transformation weitere Details hinzugefügt
	my_transform = Transform()
	my_transform.description="H264 Encodierung, welche das Video um 90 Grad dreht"
	my_transform.outputs = [transform_output]
	
	print("Die Transformation " + transform_name + " wird erstellt.")
	try:
		await client.transforms.create_or_update(
			resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
			account_name=os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"],
			transform_name=transform_name,
			parameters=my_transform),
		print(f"{transform_name} wurde erstellt oder aktualisiert, wenn sie bereits vorher existierte. ")
	except: #springt hier immer rein, todo => asynchrones Exceptiohandling anschauen
		print("Beim Erstellen der Transformation gab es einen Fehler.")
	
	client = AzureMediaServices(
    credential=token_credential,
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    )
	output_asset_name = name_prefix + "-" + my_blob.get() + "-" + uniqueness
	output_asset = client.assets.create_or_update(os.environ["AZURE_RESOURCE_GROUP"], os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"], output_asset_name, {})
	response = client.jobs.create(
    resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
    account_name=os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"],
    transform_name = transform_name,
    job_name="job1" + uniqueness,
    parameters={
	    "properties": {
            "input": {"@odata.type": "#Microsoft.Media.JobInputAsset", "assetName": my_blob.get()},
            "outputs": [{"@odata.type": "#Microsoft.Media.JobOutputAsset", "assetName": output_asset_name}],
        }
    },
    )
	print(response)

def create_content_key():
	#Erstellt eine "Richtlinie für Inhaltsschüssel". In dieser Konfiguration bekommt jeder den Schlüssel unverschlüsselt übertragen, andere Optionen sind zum Schutz der Inhalte denkbar.
	global content_key_policy_name
	content_key_policy_name= "stdpolicy_open"
	content_key_policy_description = "offener AES, ohne Key"
	content_key_policy_license = [ContentKeyPolicyPlayReadyLicense(
		allow_test_devices=True,
		license_type=ContentKeyPolicyPlayReadyLicenseType.PERSISTENT,
		content_key_location=ContentKeyPolicyPlayReadyContentEncryptionKeyFromHeader(),
		content_type=ContentKeyPolicyPlayReadyContentType.ULTRA_VIOLET_DOWNLOAD
		)]
	content_key_policy_configuration = ContentKeyPolicyClearKeyConfiguration(licenses=content_key_policy_license) #erstellt den AES Key, an der Stelle auch DRM denkbar
	content_key_policy_restriction = ContentKeyPolicyOpenRestriction() #hier andere Schutzeinstellungen denkbar
	content_key_policy_option = [ContentKeyPolicyOption(configuration=content_key_policy_configuration, restriction=content_key_policy_restriction)]
	content_key_policy = ContentKeyPolicy(description=content_key_policy_description, options=content_key_policy_option)
	print("erstelle Content Key Policy")
	client.content_key_policies.create_or_update(os.environ["AZURE_RESOURCE_GROUP"], os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"], content_key_policy_name, content_key_policy)

def show_endpoints():
	#Listet alle Endpunkte des Mediaservicekontos auf.
	# print("show_enpoints aufgerufen") #debug
	global my_endpoint
	my_endpoint = tk.StringVar()
	endpoint_list = client.streaming_endpoints.list(os.environ["AZURE_RESOURCE_GROUP"], os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"])
	n = 2
	for endpoints in endpoint_list:
		button = tk.Radiobutton(frm, text=endpoints.name, value=endpoints.name, variable=my_endpoint ,tristatevalue=0, command = lambda : print("selected endpoint: " + my_endpoint.get())).grid(column=4, row=n+1)
		# print(endpoints.name) #debug
		n=n+1

def start_endpoint():
	#Startet einen Endpunkt, der vorher per Radiobutton ausgewählt wurde. Voraussetzung ist, dass show_endpoint() mindestens einmal aufgerufen wurde.
	resp = client.streaming_endpoints.begin_start(os.environ["AZURE_RESOURCE_GROUP"], os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"], my_endpoint.get())
	# print(resp) #debug

def status_endpoint():
	#Ruft den aktuellen Status des per Radiobutton ausgewählten Endpunktes auf. Muss mindestens einmal ausgeführt werden, um eine Streaming URL zu erhalten.
	global url
	resp = client.streaming_endpoints.get(os.environ["AZURE_RESOURCE_GROUP"], os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"], my_endpoint.get())
	Label(frm, text ="Der ausgewählte Endpunkt " + str(my_endpoint.get())  +" ist " + str(resp.resource_state)).grid(column = 8, row = 1)
	url = "https://" + str(resp.host_name)+"/" #Fügt den Hostnamen des Endpunktes der URL hinzu
	# print(resp.resource_state) #debug

def stop_endpoint():
	#Stoppt den per Radiobutton ausgewählten Endpunkt.
	resp = client.streaming_endpoints.begin_stop(os.environ["AZURE_RESOURCE_GROUP"], os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"], my_endpoint.get())
	# print(resp) #debug

def create_streaming_locator(output_asset_name,locator_name,content_key_policy_name):
	#Erstellt einen Streaminglocator und stellt eine URL bereit, unter welcher das Video online verfügbar ist. Vorher muss "create_content_key" aufgerufen worden sein, um den Namen der Content Key Policy zu definieren.
    global url
	
    streaming_locator = StreamingLocator(asset_name=output_asset_name, streaming_policy_name="Predefined_ClearKey", default_content_key_policy_name=content_key_policy_name, alternative_media_id="xxx")
    locator = client.streaming_locators.create(
    resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
    account_name=os.environ["AZURE_MEDIA_SERVICES_ACCOUNT_NAME"],
    streaming_locator_name=locator_name,
    parameters=streaming_locator
    )
    splitted_name = output_asset_name.split("-") #Teilt den Namen des Outputvideos in eine Liste mit Drei Einträgen (prefix, filename, uniqueness). Benötigt, um Streaming URL zu generieren.
    # print(splitted_name) #debug
    filename_wo_extension = os.path.splitext(splitted_name[1]) #Entfernt die Dateiendung vom zweiten Eintrag der Liste. (filename)
    url = url + str(locator.streaming_locator_id) + "/" + filename_wo_extension[0] +".ism/manifest(format=m3u8-cmaf,encryption=cbc)" # zusammensetzen der m3u8 URL.
    print ("Die URL zum Abrufen des Videos ist: " + str(url))
    ttk.Label(root, text="Die URL zum Abrufen des Videos ist: " + str(url) + "\nDie URL kann aus der Konsole kopiert werden").grid(column=0, row=7, columnspan=7)
    return locator

#Zusatzfenster mit Erklärungen zu den Funktionen der Buttons
def helpwindow():
	helpwindow = Toplevel(root)
	logo = tk.PhotoImage(file = "logo.png")
	helpwindow.wm_iconphoto(False, logo)
	helpwindow.title("Hilfefenster")
	helpwindow.geometry("900x800")
	ttk.Label(helpwindow, text="Erklärungen zu den einzelnen Funktionen").grid(column=0, row=0, padx=10, pady=20, sticky="w")
	ttk.Label(helpwindow, text="Bitte die Schritte des Programms in dieser Reihenfolge durchlaufen, \nda im Verlauf Abhängigkeiten von vorherigen Funktionen enstehen können.").grid(column=1, row=0, padx=10, pady=20, sticky="w")
	ttk.Label(helpwindow, text="Versuche die Anmeldung bei Azure: ").grid(column=0, row=1, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Dieser Button erzeugt ein Login Objekt. Dieses wird benötigt, um sich gegenüber Azure zu Authentisieren.\nBitte zu Beginn auf diesen Knopf klicken. \nEine Bestätigung wird in der Konsole ausgegeben").grid(column=1, row=1, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Datei zum Upload auswählen: ").grid(column=0, row=2, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Öffnet ein Dialogfenster zum Auswählen einer Videodatei.\nDer Pfad der ausgewählten Datei wird in der Oberfläche und in der Konsole eingeblendet.").grid(column=1, row=2, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Container anzeigen: ").grid(column=0, row=3, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Listet alle im Speicheraccount gefundenen Container auf. \nMit dem Radiobutton bitte den Zielcontainer zum Speichern der Videos auswählen.").grid(column=1, row=3, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Container Erstellen: ").grid(column=0, row=4, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Dieser Knopf erstellt innerhalb des verknüpften Azure Speicherkontos \neinen Container zum Speichern von Dateien mit dem Namen, welcher in das Eingabefeld eingetragen wurde.").grid(column=1, row=4, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Datei hochladen: ").grid(column=0, row=5, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Lädt die ausgewählte Datei in den vorher bestimmten Azure Container hoch.").grid(column=1, row=5, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Zeige alle Assets \ndieses Accounte an: ").grid(column=0, row=6, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Listet alle in Azure verfügbaren Dateien auf. Hier kann das ein Video zur Transformation \noder für einen Streaming Locator ausgeählt werden. \nDazu bitte den entsprechenden Radiobutton auswählen.").grid(column=1, row=6, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Video konvertieren: ").grid(column=0, row=7, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Erstellt falls nötig ein Transform, legt einen Job zum konvertieren an und startet diesen. \nHierfür bitte das Asset auswählen, das konvertiert werden soll.").grid(column=1, row=7, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Richtlinie für \nInhaltsschlüssel erstellen: ").grid(column=0, row=8, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Erstellt eine Content Key Policy. Dieser Schritt ist nur einmal pro Streaming \nEndpunkt nötig. Hier wird festgelegt, dass das Video nicht zum Downoad bereitstehen soll, \nman kann auch Passwörter oder Zertifikate nutzen, um die Videos zu schützen.").grid(column=1, row=8, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Endpunkte anzeigen: ").grid(column=0, row=9, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Listet alle verfügbaren Endpunkte auf. \nBitte den Endpunkt, der verwendet werden soll mit dem Radiobutton auswählen.").grid(column=1, row=9, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Status des Endpunkts abfragen: ").grid(column=0, row=10, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Zeigt den aktuellen Status des ausgewählten Endpunktes an. Mögliche Status sind: stopped, starting, running, stopping").grid(column=1, row=10, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Endpunkt starten: ").grid(column=0, row=11, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Startet den vorher ausgewählten Endpunkt. \nEin Endpunkt muss im Status 'running' sein, damit Videos über ihn abgespielt werden können.").grid(column=1, row=11, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Endpunkt stoppen: ").grid(column=0, row=12, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Beendet den ausgewählten Endpunkt.").grid(column=1, row=12, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Streaminglocator erstellen: ").grid(column=0, row=13, padx=10, pady=10, sticky="w")
	ttk.Label(helpwindow, text="Erstellt einen Streaming Locator, welcher dann eine URL bereitstellt, \num das ausgewählte Asset (Video) im Internet abzuspielen. \n Die URL kann aus der Konsole kopiert werden").grid(column=1, row=13, padx=10, pady=10, sticky="w")





#Hauptmenü und Erstellung der GUI Objekte
root = Tk()
root.geometry("1500x250")
frm = ttk.Frame(root, padding=10)
frm.grid()
root.title("SKILL/ELLE Videos zu Azure hochladen und streamen")
logo = tk.PhotoImage(file = "logo.png")
root.wm_iconphoto(False, logo)
ttk.Button(frm, text="Hilfe und Erklärungen", command = helpwindow).grid(column=0, row=0, sticky='nesw')
ttk.Button(frm, text="Versuche die Anmeldung bei Azure", command=signin).grid(column=0, row=1, sticky='nesw')
ttk.Button(frm, text="Datei zum Hochladen auswählen", command=select_data).grid(column=0, row=2, sticky='nesw')
ttk.Button(frm, text="Datei hochladen", command=upload_data).grid(column=0, row=3, sticky='nesw')
ttk.Label(frm, text="").grid(column=0, row=4, sticky='nesw')
ttk.Button(frm, text="Programm beenden", command=root.destroy).grid(column=0, row=5, sticky='nesw')

container_name_default = StringVar(root, value="Name eingeben...")
container_name = tk.Entry(frm, textvariable=container_name_default)
container_name.grid(column=1, row=0)

ttk.Button(frm, text="Container erstellen", command = create_container).grid(column=2, row=0, sticky='nesw')
ttk.Button(frm, text="Container anzeigen", command=lambda: show_container(blob_service_client)).grid(column=2, row=1, sticky='nesw')

ttk.Button(frm, text="zeige alle Assets dieses Accounts an", command=lambda: show_blobs(blob_service_client)).grid(column=3, row=0, sticky='nesw')

ttk.Button(frm, text="Video konvertieren", command=lambda: asyncio.run(create_transform())).grid(column=4, row=0, sticky='nesw')
ttk.Button(frm, text="Richtlinien für Inhaltsschlüssel erstellen", command=create_content_key).grid(column=4, row=1, sticky='nesw')
ttk.Button(frm, text="Endpunkte anzeigen", command = show_endpoints).grid(column=4, row=2, sticky='nesw')

ttk.Button(frm, text="Endpunkt starten", command = start_endpoint).grid(column=5, row=0, sticky='nesw')
ttk.Button(frm, text="Status des Endpunkts abfragen", command = status_endpoint).grid(column=5, row=1, sticky='nesw')
ttk.Button(frm, text="Endpunkt stoppen", command = stop_endpoint).grid(column=5, row=2, sticky='nesw')
streaminglocator_name_default = StringVar(root, value="Name eingeben...")
streaminglocator_name = tk.Entry(frm, textvariable=streaminglocator_name_default)
streaminglocator_name.grid(column=5, row=3, sticky='nesw')
ttk.Button(frm, text="Streaminglocator erstellen", command =lambda: create_streaming_locator(my_blob.get(), streaminglocator_name.get(), content_key_policy_name)).grid(column=5, row=4, sticky='nesw')

root.mainloop()

