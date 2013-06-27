package skins
{
	
	import spark.components.Image;
	import spark.components.supportClasses.SkinnableComponent;
	
	import mx.core.BitmapAsset;
	import spark.components.Image;
	import spark.skins.mobile.ViewNavigatorApplicationSkin;
	
	public class kirstyskin extends SkinnableComponent
	{
		private var image:Image;
		
		[Embed(source="assets/BG.jpg")]
		private var background:Class;
		
		public function kirstyskin()
		{
			super();
		}
		
		override protected function getCurrentSkinState():String
		{
			return super.getCurrentSkinState();
		} 
		
		override protected function partAdded(partName:String, instance:Object) : void
		{
			super.partAdded(partName, instance);
		}
		
		override protected function partRemoved(partName:String, instance:Object) : void
		{
			super.partRemoved(partName, instance);
		}
		
		override protected function createChildren():void {
			image = new Image();
			//Replace the right side below with your source (including URL)
			image.source = (new background() as BitmapAsset);
			image.height = 600; //Set image size here
			image.width = 1024;
			this.addChild(image);
			
			super.createChildren();
		}
		
	}
}