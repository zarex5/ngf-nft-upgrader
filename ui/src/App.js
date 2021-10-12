import React from 'react';
import { loadNGFs } from './web3/loadNGFs';
import { generateUpdateTx } from './web3/generateUpdateTx';
import { ATTRIBUTES_LIST } from './data/attributes';
import { Connection } from '@solana/web3.js';

import './Home.css';
import './App.css';
import './Bootstrap.css';

const ENDPOINT = "https://token.nogoal.click:5050/ngf-img";
const NETWORK = "https://api.mainnet-beta.solana.com";

const SOL_FEES = 0.05;

class App extends React.Component {
    
    constructor(props) {
        super(props);

        this.state = {
          addr: "",
          data: [],
          selectedData: null,
          untouchedData: null,
          total: 0,
          messages: {
            success: "",
            error: ""
          }
        };
    }

    addressLoad() {
      let addrStr = document.getElementById("addrInput").value;
      if(addrStr.length < 43 || addrStr.length > 44) {
        alert("Not a valid SOL address");
        return;
      }

      this.setState({addr: addrStr});
      loadNGFs(addrStr).then(res => {
        this.setState({data: res});
      });
    }

    prepPopUp(data) {
      this.resetMessages();
      let attrs = ATTRIBUTES_LIST.map(x => x.values).flat();
      for(let i=0; i<data.attributes.length; i++) {
        let list = attrs.filter(x => (x.value == data.attributes[i].value));
        let price = 0;
        if(list.length > 0)
          price = list[0].price;
        else
          console.log("Did not find a price for ", data.attributes[i]);
        data.attributes[i].currentPrice = price;
        data.attributes[i].newPrice = price/2;
        data.attributes[i].selectedValue = data.attributes[i].value;
      }
      this.setState({selectedData: data});
      this.setState({untouchedData: JSON.parse(JSON.stringify(data))});
    }

    handleChange(event, type) {
      let value = event.target.value;
      let attrs = ATTRIBUTES_LIST.map(x => x.values).flat();
      let newPrice = attrs.filter(x => (x.value == value))[0].price;

      let selectedData = this.state.selectedData;
      let selectedAttr = selectedData.attributes.filter(x => x.trait_type == type)[0];
      selectedAttr.newPrice = newPrice;
      selectedAttr.selectedValue = value;
      this.setState({selectedData: selectedData});
      this.previewImg();
    }

    resetPopup() {
      let clean = this.state.untouchedData;
      this.setState({selectedData: JSON.parse(JSON.stringify(clean))});
      document.getElementById("popup-pic").src = this.state.untouchedData.image;
      this.resetMessages();
    }

    computePrice(el) {
      return this.state.selectedData.attributes.filter(x => (x.trait_type == el.type))[0].currentPrice/2 - this.state.selectedData.attributes.filter(x => (x.trait_type == el.type))[0].newPrice;
    }

    computeTotalPrice() {
      return this.state.selectedData.attributes.map(x => x.currentPrice/2 - x.newPrice).reduce((prev, next) => prev + next);
    }

    computeSelectedLayers() {
      let attrs = ATTRIBUTES_LIST.map(x => x.values.map(y => {y.type = x.type; return y;})).flat();
      let layers = [];
      this.state.selectedData.attributes.forEach(x => {
        let attributeProp = attrs.filter(attr => attr.value == x.selectedValue && attr.type == x.trait_type)[0];
        if(attributeProp != null) 
          layers.push(attributeProp.layer);
      });
      return layers;
    }

    setSuccessMsg(content) {
      this.setState({messages: {success: content, error: ""}});
    }

    setErrorMsg(content) {
      this.setState({messages: {success: "", error: content}});
    }

    resetMessages() {
      this.setState({messages: {success: "", error: ""}});
    }

    previewImg() {
      let layers = this.computeSelectedLayers();
      console.log(layers);
      document.getElementById("popup-pic").src = ENDPOINT + "?layers=" + layers.join(",");
    }

    async validate() {
      let code = prompt("Please enter your BETA access code:", "");
      if (code == null || code != "IGNITION002") {
        alert("Sorry, invalid BETA access code");
      } else {
        let provider = this.getProvider();
        console.log("Provider", provider);
        if(provider == null)
          return;
        window.solana.connect();
        window.solana.on("connect", () => {
          console.log("Connected!", window.solana.publicKey.toString());
          this.sendTransaction();
        });
      }
    }

    getProvider = () => {
      if ("solana" in window) {
        const provider = window.solana;
        if (provider.isPhantom) {
          return provider;
        }
      }
      this.setErrorMsg("Please install Phantom wallet to use this app! <a href='https://phantom.app/' target='_blank' rel='noreferrer'>https://phantom.app/</a>");
      return null;
    }

    async sendTransaction() {
      let kInoFees = this.computeTotalPrice()*-1;
      if(kInoFees < 0) {
        this.setErrorMsg("Can't downgrade a face, INO amount has to be negative. You can use refunds from removed attributes to buy better ones!");
        return;
      } else {
        try {
          const connection = new Connection(NETWORK);
          let layers = this.computeSelectedLayers();
          let mint = this.state.selectedData.mint;
          const transaction = await generateUpdateTx(mint, layers, SOL_FEES, kInoFees, connection, window.solana.publicKey);
          console.log("transaction", transaction);
          const signedTransaction = await window.solana.signTransaction(transaction);
          const signature = await connection.sendRawTransaction(signedTransaction.serialize());
          console.log(signature);
          this.setSuccessMsg("Transaction sent! Upgrade can take a few minutes. Please keep the signature as payment proof: <a href='https://explorer.solana.com/tx/" + signature + "' target='_blank' rel='noreferrer'>" + signature + "</a>");
        } catch (ex) {
          if(ex.message.includes("Signature request denied") || ex.message.includes("Could not find a INO token account")) {
            this.setErrorMsg(ex.message);
          } else {
            let fundsMsg = "Make sure you have at least " + kInoFees + "k INO" + " and ◎" + SOL_FEES + " + ◎0.000005 to cover network fees!";
            this.setErrorMsg(ex.message + " - " + fundsMsg);
          }
        }
      }
    }

    render() {
        return (
          <div className="App">
            <div className="container">
              <div className="row mt-3">
                <div className="col-2">
                  <a href="/" type="button" className="btn btn-light form-control-lg btn-back" style={{marginRight: '30px'}}><i className='fa fa-angle-left'></i> Back to website</a>
                </div>
                <div className="col-10">
                  <div className="alert alert-primary" role="alert">
                    <i className='fa fa-info-circle'></i> The attributes upgrade system is in beta (with access code required), please report any issue on our Discord!
                  </div>
                </div>
              </div>
              <div className="input-group mb-3">
                <input type="text" id="addrInput" className="form-control form-control-lg" placeholder="Input your SOL address"/>
                <div className="input-group-append">
                  <button className="btn btn-dark" type="button" onClick={() => { this.addressLoad()}}>
                    <i className='fa fa-cog'></i> Load NGFs
                  </button>
                </div>
              </div>
              {
                this.state.addr.length != 0 && this.state.data.length == 0 ? <p className="white"><i className='fa fa-exclamation-circle'></i> No NGFs found on this address!</p> : ""
              }
              <div className="row">
                {
                  this.state.data.map(el => 
                    <div className="pc25" key={el.name}>
                      <div className="card" style={{width: '18rem'}}>
                        <img className="card-img-top" src={el.image} alt="Card image cap"/>
                        <div className="card-body">
                          <h5 className="card-title">{el.name}</h5>
                          <div className="card-text card-text-l">
                            {
                            el.attributes != null ? 
                              el.attributes.map(attr => 
                                <p key={attr.trait_type}>{attr.trait_type}: {attr.value}</p>
                              ) : ""
                            }
                          </div>
                        </div>
                        <ul className="list-group list-group-flush" data-toggle="modal" data-target="#exampleModal" onClick={() => { this.prepPopUp(el)}}>
                          <li className="list-group-item list-size">
                            <a><i className='fa fa-wrench'></i> Upgrade</a>
                          </li>
                        </ul>
                      </div>
                    </div>
                  )
                }
              </div >
            </div>

            <div className="modal fade" id="exampleModal" tabIndex="-1" role="dialog" aria-labelledby="exampleModalLabel" aria-hidden="true">
              <div className="modal-dialog" role="document">
                { this.state.selectedData != null ?
                  <div className="modal-content">
                    <div className="modal-header">
                      <h5 className="modal-title" id="exampleModalLabel">Upgrade {this.state.selectedData.name}</h5>
                      <button type="button" className="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                      </button>
                    </div>
                    <div className="modal-body">
                      <div className="row">
                        <div className="col-6">
                          <img className="card-img-top card-img-top-l" id="popup-pic" src={this.state.selectedData.image} alt="Card image cap"/>
                          <div className="buttons">
                            <button type="button" className="btn btn-secondary mr-2" onClick={() => { this.resetPopup()}}><i className='fa fa-undo'></i> Reset</button>
                            <button type="button" className="btn btn-secondary mr-2" onClick={() => { this.previewImg()}}><i className='fa fa-eye'></i> Update preview</button>
                            <button type="button" className="btn btn-primary" title="Coming soon!" onClick={() => { this.validate()}}><i className='fa fa-shopping-basket'></i> Confirm!</button>
                          </div>
                        </div>
                        <div className="col-6">
                          <form>
                            { ATTRIBUTES_LIST.map(el => 
                              <div className="form-group form-control-sm row less-bottom" key={el.type}>
                                <label className="col-sm-2 col-form-label">{el.type}</label>
                                <div className="col-sm-7">
                                  <select className="form-control form-control-sm" value={this.state.selectedData.attributes.filter(x => (x.trait_type == el.type))[0].selectedValue} onChange={(e) => this.handleChange(e, el.type)}>
                                    { el.values.map(attr => 
                                      <option key={attr.value} value={attr.value}>
                                        {this.state.selectedData.attributes.filter(x => (x.trait_type == el.type))[0].value == attr.value ? "• " : ""}{attr.value} ({attr.price}k)
                                      </option>
                                    )}
                                  </select>
                                </div>
                                <div className={`col-sm-3 span-price ${this.computePrice(el)>0 ? 'price-positive' : 'price-negative'}`}>
                                  {
                                    this.computePrice(el) != 0 ? 
                                      (this.computePrice(el) > 0 ? "+" : "") + this.computePrice(el) + "k INO"
                                      : ""
                                  }
                                </div>
                              </div>
                            )}
                          </form>
                          <hr/>
                          <div className="form-group form-control-sm row less-bottom">
                            <label className="col-sm-2 col-form-label">Total</label>
                            <div className="col-sm-7 span-sol-price">
                              - ◎{SOL_FEES}
                            </div>
                            <div className="col-sm-3 span-price">
                              {
                                this.computeTotalPrice() != 0 ? 
                                  (this.computeTotalPrice() > 0 ? "+" : "") + this.computeTotalPrice() + "k INO"
                                  : "- 0 INO"
                              }
                            </div>
                          </div>
                        </div>
                      </div>
                      { this.state.messages.success.length > 0 &&
                        <div className="alert alert-success alert-bottom" role="alert">
                          <i className='far fa-check-circle'></i> <span className="content" dangerouslySetInnerHTML={{__html: this.state.messages.success}}></span>
                        </div>
                      }
                      { this.state.messages.error.length > 0 &&
                        <div class="alert alert-danger alert-bottom" role="alert">
                          <i className='far fa-times-circle'></i> <span className="content" dangerouslySetInnerHTML={{__html: this.state.messages.error}}></span>
                        </div>
                      }
                    </div>
                  </div>
                  : ""
                }
              </div>
            </div>
          </div>
        );
    }
}

export default App;