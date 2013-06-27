package 
{
	import flash.events.Event;
	import flash.events.HTTPStatusEvent;
	import flash.events.IOErrorEvent;
	import flash.events.SecurityErrorEvent;
	import flash.net.URLLoader;
	import flash.net.URLLoaderDataFormat;
	import flash.net.URLRequest;
	import flash.net.URLRequestMethod;
	import flash.utils.Dictionary;
	
	import mx.collections.ArrayCollection;
	
	//import org.httpclient.http;

	public class Wrapper
	{
		public static var session_id:String;
		public static var callback:Function = null;
		public function Wrapper(){
		}
		
		
		/*=========================================================================================================
						REGISTER, LOGIN, LOGOUT
		============================================================================================================*/
		
		public static function register(func:Function, phone:String, name:String, pwd:String):void {
			callback = func;
			//Make a data object

			var data:Object = new Array(phone, name, pwd);
			data.phone = phone;
			data.name = name;
			data.password = pwd;
			print("Register function");
			genLoader().load(genRequest("http://111.67.18.188/register", URLRequestMethod.POST, JSON.stringify(data)));
		}
			
		public static function login(func:Function, phone:String, pwd:String):void{
			callback = func;
			print("Login function");
			//Combine phone & password into object
			//var data = new Array(phone, password);
			var dict:Object = new Object();
			dict.phone_number = phone;
			dict.password = pwd;
			
			print(JSON.stringify(dict));
			genLoader().load(genRequest("http://111.67.18.188/login", URLRequestMethod.POST, JSON.stringify(dict)));
		}		
	
		public static function logout():void{
			print("Logout function");
			//Apparently no params at all -is this right?
			var data:Object = new Object();
			data.session_id = session_id;
			genLoader().load(genRequest("http://111.67.18.188/logout", URLRequestMethod.POST, JSON.stringify(data)));
			session_id = null;
		}
		
		/*=================================================================================================
								OPERATIONS ON GROUPS
		==================================================================================================*/
		

		
		public static function createGroup(func:Function, data:Array):void{
			callback = func;
			print("Create group function");
			genLoader().load(genRequest("http://111.67.18.188/group", URLRequestMethod.POST, JSON.stringify(data)));	
		}
		
		public static function deleteGroup(func:Function, group_id):void{
			callback = func;
			print("Delete group function");
			//group id could be string or int
			//not sure if it will work just like this:
			genLoader().load(genRequest("http://111.67.18.188/group", URLRequestMethod.DELETE, JSON.stringify(group_id)));
		}
		public static function getPassengerGroups(func:Function):void{
			callback = func;
			print("Get passenger groups function");
			var data:Object = new Object();
			data.session_id = session_id;
			data.__method__ = "getPassengerGroups";
			//No params?
			genLoader().load(genRequest("http://111.67.18.188/doeverything", URLRequestMethod.POST, void));
		}
		
		public static function getPassengers(func:Function):void{
			print("getPassengers function");
			callback = func;
			var data:Object = new Object();
			data.session_id = session_id;
			data.__method__ = "getPassengers";

			//no params?
			genLoader().load(genRequest("http://111.67.18.188/doeverything", URLRequestMethod.POST, void));
		}
		
		public static function deletePassenger(func:Function, user_id_to_del:String, group_id:String):void{
			callback = func;
			print("Delete passenger function");
			var data:Object = new Object();
			data.user_id = user_id_to_del;
			data.group_id = group_id;
			data.session_id = session_id;
			genLoader().load(genRequest("http://111.67.18.188/passengers", URLRequestMethod.DELETE, JSON.stringify(data)));
		}
		
		public static function addPassenger(group_id:String, user_to_add_id:String, phone_number:String):void{
			//Make data object
			print("Add passenger function");
			var data:Object = new Object();
			data.group_id = group_id;
			data.user_id = user_to_add_id;
			data.phone_number = phone_number;
			data.session_id = session_id;
			genLoader().load(genRequest("http://111.67.18.188/passengers", URLRequestMethod.POST, JSON.stringify(data)));
		}
		
		
		public static function getGroup(func:Function, group_id:String, group_name:String):void{
			//TODO: Make an object of group id and group name, and pass it as 3rd param
			callback = func;
			print("get group function");
			var data:Object = new Object();
			data.session_id = session_id;
			data.group_id = group_id;
			data.group_name = group_name;
			data.__method__ = "getGroup";
			genLoader().load(genRequest("http://111.67.18.188/doeverything", URLRequestMethod.POST, JSON.stringify(data)));	
			//returns a dict containing the group data
		}
		
		public static function updateGroup(returnTo:Function, group_id, name, origin, destination, arrival_time, dep_time, seats, days):void{
			callback = returnTo;
			print("update group function");
			//Make an object out of those fields (pay attention to type!) & pass as 3rd param
			var data:Object = new Object();
			data.session_id = session_id;
			data.name = name;
			data.origin = origin;
			data.destination = destination;
			data.arrival_time = arrival_time;
			data.departure_time = dep_time;
			data.seats = seats;
			data.days = days;
			data.group_id = group_id;
			genLoader().load(genRequest("http://111.67.18.188/group", URLRequestMethod.PUT, JSON.stringify(data)));	
			//returns a dict containing the group data

		}
		
		public static function getDriverGroups(func:Function):void{
			callback = func;
			print("get driver groups function");
			// Attempt to get repsonse from server.
			var data:Object = new Object();
			data.session_id = session_id;
			data.__method__ = "getDriverGroups";
			//Apparently takes no params?
		//	var client:HttpClient = new HttpClient();
			//var uri:URI = new URI("http://111.67.18.188/driverGroups");
			//var request:HttpRequest = new HttpRequest(URLRequestMethod.GET, null, JSON.stringify(data));
				
			print("Ses id:");
			print(session_id);

				genLoader().load(genRequest("http://111.67.18.188/doeverything", URLRequestMethod.POST, JSON.stringify(data)));
			
		}

		/*===================================================================================================
									SEARCH
		======================================================================================================*/
		
		public static function search(func:Function, name:String):void{
			callback = func;
			print("Search function");
			var data:Object = new Object();
			data.name = name;
			data.session_id = session_id;
			data.__method__ = "searchGroups";
			genLoader().load(genRequest("http://111.67.18.188/doeverything", URLRequestMethod.POST, JSON.stringify(data)));
		}
		
		public static function searchGroups(func:Function):void{
			callback = func;
			print("Search groups function");
			var data:Object = new Object();
			data.session_id = session_id;
			data.__method__ = "searchGroups";
			genLoader().load(genRequest("http://111.67.18.188/doeverything", URLRequestMethod.POST, JSON.stringify(session_id)));
			//returns lots of JSON

		}
		
		/* ====================================================================================================
						NOTIFICATIONS METHODS
		======================================================================================================*/
		
		public static function groupRequest(){
			print("group request function");
			genLoader().load(genRequest("http://111.67.18.188/getDriverGroups", URLRequestMethod.GET,void));
		}
		
		public static function getNotifications(func:Function):void{
			callback = func;
			print("get notifications function");
			var data:Object = new Object();
			data.session_id = session_id;
			data.__method__ = "getNotifications";
			genLoader().load(genRequest("http://111.67.18.188/doeverything", URLRequestMethod.POST, JSON.stringify(data)));
		}
		
		public static function createGroupInvite(user_id, phone_number, group_id):void{
			var data:Object = new Object();
			print("create group invite function");
			data.session_id = session_id;
			data.user_id = user_id;
			data.group_id = group_id;
			data.phone_number = phone_number;
			genLoader().load(genRequest("http://111.67.18.188/groupinvite", URLRequestMethod.POST, JSON.stringify(data)));
		}
		
		public static function acceptGroupInvite():void{
			print("Accept group invite function");
			var data:Object = new Object();
			data.session_id = session_id;
			genLoader().load(genRequest("http://111.67.18.188/acceptgroupinvite", URLRequestMethod.POST, JSON.stringify(data)));
			//returns nothing
		}
		
		public static function createGroupRequest(group_id):void{
			//POST
			print("Create group request function");
			var data:Object = new Object();
			data.session_id = session_id;
			data.group_id = group_id;
			genLoader().load(genRequest("http://111.67.18.188/grouprequest", URLRequestMethod.POST, JSON.stringify(data)));
		}
		
		public static function acceptGroupRequest():void{
			print("Accept group request function");
			genLoader().load(genRequest("http://111.67.18.188/acceptgrouprequest", URLRequestMethod.POST,void));
			//returns nothing

		}
		
		public static function declineGroupInvite():void{
			genLoader().load(genRequest("http://111.67.18.188/declinegroupinvite", URLRequestMethod.POST,void));
			//returns nothing
			print("Decline group invite function");

		}
		
		public static function declineGroupRequest():void{
			print("Decline group request function");
			genLoader().load(genRequest("http://111.67.18.188/declinegrouprequest", URLRequestMethod.POST,void));
			//returns nothing

		}

		
		
		//var requestVars:URLVariables = new URLVariables();
		//requestVars.icp = "0000067894TR-CE6";
		//requestVars.raw_start = "2013-11-01";
		
		//return requestVars;
		//}
		
		// Generates a request.  1st param - URL, 2nd param - http method, 3rd - JSON data
		private static function genRequest(urlString, method, data):URLRequest
		{
			var request:URLRequest = new URLRequest();
			request.url = urlString;
			request.method = method; 
			request.data = data;
			request.contentType = "application/json";
			return request;
		}
		
		// Generates a loader, and applies callbacks.
		private static function genLoader():URLLoader
		{
			var loader:URLLoader = new URLLoader();
			loader.dataFormat = URLLoaderDataFormat.TEXT;
			loader.addEventListener(Event.COMPLETE, loaderCompleteHandler);
			loader.addEventListener(HTTPStatusEvent.HTTP_STATUS, httpStatusHandler);
			loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR, securityErrorHandler);
			loader.addEventListener(IOErrorEvent.IO_ERROR, ioErrorHandler);
			
			return loader;
		}
		
		// Activates when we get a response from the request.
		private static function loaderCompleteHandler(e:Event):void
		{
			try 
			{
				print(e.target.data);
				//var res:Object = JSON.parse(e.target.data);
				//for (var gi in res) {
				//	print(res[gi].group_name);
				//}
				callback(e);
			}
			catch (e:Error)
			{
				print("Failed to parse JSON: " + e.message);
			}

		}
		
		
		// Error handling - prints errors to console, if request fails.
		private static function httpStatusHandler(e:Event):void
		{
			print("httpStatusHandler:" + e.toString());
		}
		
		private static function securityErrorHandler (e:Event):void
		{
			print("securityErrorHandler:" + e.toString());
		}
		
		private static function ioErrorHandler(e:Event):void
		{
			print("ioErrorHandler: " + e.toString());
		}
		
		
		// A function to output messages on the screen and trace them in the console
		public static function print(str:String):void
		{
			//output = str;
			trace(str);
		}

	}
}