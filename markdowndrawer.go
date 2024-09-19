package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type TableRow struct {
	VnetLink string
	Location string
	IP       string
	Peerings string
	Subnets  string
}

type JSONResult struct {
	Rows []TableRow
}

type JSONData struct {
	Name       string     `json:"name"`
	ID         string     `json:"id"`
	Location   string     `json:"location"`
	Properties Properties `json:"properties"`
}

type Properties struct {
	AddressSpace AddressSpace `json:"addressSpace"`
	Subnets      []Subnet     `json:"subnets"`
	Peerings     []Peering    `json:"virtualNetworkPeerings"`
}

type AddressSpace struct {
	AddressPrefixes []string `json:"addressPrefixes"`
}

type Subnet struct {
	Properties SubnetProperties `json:"properties"`
}

type SubnetProperties struct {
	AddressPrefixes []string `json:"addressPrefixes"`
	AddressPrefix   string   `json:"addressPrefix"`
}

type Peering struct {
	Name       string            `json:"name"`
	Properties PeeringProperties `json:"properties"`
}

type PeeringProperties struct {
	PeeringState string     `json:"peeringState"`
	SyncLevel    string     `json:"peeringSyncLevel"`
	RemoteVnet   RemoteVnet `json:"remoteVirtualNetwork"`
}

type RemoteVnet struct {
	ID string `json:"id"`
}

var userAccount string

func parseJSON(data []byte, result *JSONResult) {
	var jsonData JSONData

	err := json.Unmarshal(data, &jsonData)
	if err != nil {
		fmt.Println(err)
		return
	}

	ip := strings.Join(jsonData.Properties.AddressSpace.AddressPrefixes, ";")
	subnets := ""
	if len(jsonData.Properties.Subnets) > 0 {
		for _, subnet := range jsonData.Properties.Subnets {
			if len(subnet.Properties.AddressPrefixes) > 0 {
				subnets += strings.Join(subnet.Properties.AddressPrefixes, ";") + ";"
			} else {
				subnets += subnet.Properties.AddressPrefix + ";"
			}
		}
	} else {
		subnets = ""
	}

	peerings := ""
	for _, peering := range jsonData.Properties.Peerings {
		peerings += fmt.Sprintf("[%s](https://portal.azure.com/#@%s/resource%s) - %s, %s;",
			peering.Name, userAccount, peering.Properties.RemoteVnet.ID, peering.Properties.SyncLevel, peering.Properties.PeeringState)
	}

	vnetLink := fmt.Sprintf("[%s](https://portal.azure.com/#@%s/resource%s)",
		jsonData.Name, userAccount, jsonData.ID)

	row := TableRow{
		VnetLink: vnetLink,
		Location: jsonData.Location,
		IP:       ip,
		Peerings: peerings,
		Subnets:  subnets,
	}

	// Add the parsed data to the result
	result.Rows = append(result.Rows, row)
}

func printResults(result *JSONResult, outputFileName string) {
	output := "| VNet | Location | IP | Peerings | Subnets |\n"
	output += "| -------- | ------- | ------- | ------- | ------- |\n"
	for _, row := range result.Rows {
		output += fmt.Sprintf("| %s | %s | %s | %s | %s |\n", row.VnetLink, row.Location, row.IP, row.Peerings, row.Subnets)
	}

	if outputFileName != "" {
		err := os.WriteFile(outputFileName, []byte(output), 0644)
		if err != nil {
			fmt.Println("Error writing to file:", err)
			return
		}
		fmt.Println("Results written to", outputFileName)
	} else {
		fmt.Print(output)
	}
}

func generateMarkdownTable(dir, resultPath string) {
	// Stores the parsed JSON data as a Markdown table
	result := &JSONResult{}

	files := []os.FileInfo{}

	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			fmt.Println(err)
			return nil
		}
		if info != nil && !info.IsDir() && filepath.Ext(path) == ".json" {
			files = append(files, info)
		}
		return nil
	})

	if err != nil {
		fmt.Println(err)
		return
	}

	// Sort files by modification time in descending order
	sort.Slice(files, func(i, j int) bool {
		return files[i].ModTime().After(files[j].ModTime())
	})

	for _, file := range files {
		path := filepath.Join(dir, file.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			fmt.Println(err)
			continue
		}
		parseJSON(data, result)
	}

	// Now you can print all parsed JSON data
	printResults(result, resultPath)
}
func main() {
	userAccount = os.Getenv("AZURE_TENANT_ID")
	if userAccount == "" {
		fmt.Println("[ERR] AZURE_TENANT_ID not set")
		return
	}

	dir := os.Getenv("PEERINGS_DIR")
	if dir == "" {
		dir = "peerings"
	}

	tablePath := os.Getenv("TABLE_PATH")
	if tablePath == "" {
		tablePath = "Documentation/VNet-peerings-report.md"
	}

	generateMarkdownTable(dir+"/", tablePath)
}
