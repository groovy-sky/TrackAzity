package main  
  
import (  
    "io/ioutil"  
    "log"  
    "net/http"  
    "os"  
)  
  
func main() {  
    // Read the URL from the environment variable  
    url := os.Getenv("URL")  
    if url == "" {  
        log.Fatal("URL environment variable not set")  
    }  
  
    // Send HTTP GET request  
    resp, err := http.Get(url)  
    if err != nil {  
        log.Fatal(err)  
    }  
    defer resp.Body.Close()  
  
    // Read the response  
    body, err := ioutil.ReadAll(resp.Body)  
    if err != nil {  
        log.Fatal(err)  
    }  
  
    // Print the response to console  
    log.Println(string(body))  
}  
