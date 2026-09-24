from pathlib import Path
p=Path(r'F:\H3-Music\app.py');s=p.read_text(encoding='utf-8').replace('except (BrokenPipeError,ConnectionResetError): pass','except ConnectionError: pass')
s=s.replace("  except PermissionError as e: self.json_response({'error':str(e)},403)\n  except Exception as e: self.json_response({'error':str(e)},400)\n\ndef main():", "  except ConnectionError: pass\n  except PermissionError as e: self.json_response({'error':str(e)},403)\n  except Exception as e: self.json_response({'error':str(e)},400)\n\ndef main():")
p.write_text(s,encoding='utf-8')
