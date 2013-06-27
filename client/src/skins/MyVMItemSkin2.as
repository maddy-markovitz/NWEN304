package skins
{
	import mx.core.BitmapAsset;
	import spark.components.Image;
	import spark.skins.mobile.ViewNavigatorApplicationSkin;

	
	public class MyVMItemSkin2 extends ViewNavigatorApplicationSkin
	{
		private var image:Image;
		
		[Embed(source="/assets/BG.jpg")]
		private var background:Class;
		
		public function MyVMItemSkin2()
		{
			super();
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