using System;
using System.IO;
using System.Net;
using System.Diagnostics;
using System.Threading;
using System.Windows.Forms;
using System.Reflection;
[assembly: AssemblyTitle("H3-Music")]
[assembly: AssemblyProduct("H3-Music")]
[assembly: AssemblyVersion("1.0.0.0")]
class H3Music {
 const string Url="http://127.0.0.1:8776";
 static bool Healthy() { try { var q=(HttpWebRequest)WebRequest.Create(Url+"/api/health");q.Proxy=null;q.Timeout=1200;using(var r=q.GetResponse())using(var s=new StreamReader(r.GetResponseStream()))return s.ReadToEnd().Contains("\"app\": \"H3-Music\""); } catch {return false;} }
 [STAThread] static void Main(string[] args) {
  string root=AppDomain.CurrentDomain.BaseDirectory;
  try {
   if(args.Length>0 && args[0]=="--stop") {
    if(Healthy()){ var q=(HttpWebRequest)WebRequest.Create(Url+"/api/shutdown");q.Method="POST";q.Proxy=null;q.ContentType="application/json";q.Headers["X-H3-Music"]="1";byte[] b=System.Text.Encoding.UTF8.GetBytes("{}");q.ContentLength=b.Length;using(var s=q.GetRequestStream())s.Write(b,0,b.Length);using(var r=q.GetResponse()){} }
    return;
   }
   using(var mutex=new Mutex(false,"Local\\H3MusicLaunch")) {
    if(!mutex.WaitOne(30000))throw new Exception("Avvio già in corso.");
    try {
     if(!Healthy()) {
      string python=Path.Combine(root,"runtime","python","pythonw.exe");
      if(!File.Exists(python))throw new Exception("Runtime Python non trovato nella cartella H3-Music.");
      var start=new ProcessStartInfo(python,"\""+Path.Combine(root,"app.py")+"\"");start.WorkingDirectory=root;start.UseShellExecute=false;start.CreateNoWindow=true;
      Process.Start(start);
      for(int i=0;i<80&&!Healthy();i++)Thread.Sleep(250);
      if(!Healthy())throw new Exception("Il server non si è avviato. Controllare logs/server.log e la porta 8776.");
     }
    } finally {mutex.ReleaseMutex();}
   }
   string edge=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),"Microsoft","Edge","Application","msedge.exe");
   if(!File.Exists(edge))edge=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),"Microsoft","Edge","Application","msedge.exe");
   if(File.Exists(edge)) {
    var browser=new ProcessStartInfo(edge,"--app="+Url+" --user-data-dir=\""+Path.Combine(root,"data","window-profile")+"\" --no-first-run --disable-extensions");browser.UseShellExecute=false;browser.CreateNoWindow=true;Process.Start(browser);
   } else Process.Start(Url);
  } catch(Exception e) {MessageBox.Show(e.Message,"H3-Music",MessageBoxButtons.OK,MessageBoxIcon.Error);}
 }
}
