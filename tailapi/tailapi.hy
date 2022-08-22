(import rich.traceback)
(.install rich.traceback :show-locals True)

(import ast)
(import json)
(import magicattr)
(import oreo)
(import requests)

(import addict [Dict])
(import autoslot [Slots])
(import click)
(import collections [ChainMap])
(import functools [partial])
(import ipaddress [ip-address])
(import more-itertools [intersperse])
(import operator [attrgetter])
(import os [environ])
(import pathlib [Path])
(import rapidfuzz [process fuzz])
(import requests.auth [HTTPBasicAuth])
(import rich [print])
(import rich.pretty [pprint])

(try (import coconut *)
     (except [ImportError] None))

(try (import cytoolz [first])
     (except [ImportError]
             (import toolz [first])))

(require hyrule [-> assoc unless])

(defn raise-response-error [error-message response]
      (raise (ValueError (+ error-message " Response reason: " response.reason))))

(defn return-json-addict [action error-message #* args #** kwargs]
      (let [ response ((getattr requests action) #* args #** kwargs) ]
           (if (= (getattr response "status_code") 200)
               (return (Dict (.loads json response.text)))
               (raise-response-error error-message response))))

(defclass Transformer [ ast.NodeTransformer ]
          (setv ALLOWED-NAMES (set [

                                     ])
                ALLOWED-NODE-TYPES (set [ "Expression"
                                          "BoolOp"
                                          "And"
                                          "Constant"
                                          "Or" ]))
                                          
          (defn generic-visit [ self node ]
                (setv nodetype (getattr (type node) "__name__"))
                (unless (in nodetype self.ALLOWED-NODE-TYPES)
                        (raise (RuntimeError f"Invalid expression: {nodetype} not allowed")))
                (return (.generic-visit ast.NodeTransformer self node))))

(defclass Group []
          (defn __init__ [ self
                           [delimiter ""]
                           [dk None]
                           [ephemeral False]
                           [excluded-tags #()]
                           [groups None]
                           [not-ephemeral False]
                           [not-preauthorized False]
                           [not-reusable False]
                           [preauthorized False]
                           [reusable False]
                           [tags #()]
                           [using-keys False]
                           [value None]
                           [verbose False] ]
                (setv self.delimiter delimiter
                      self.dk dk
                      self.ephemeral ephemeral
                      self.excluded-tags excluded-tags
                      self.original-groups groups
                      self.groups (.replace-all self self.original-groups)
                      self.not-ephemeral not-ephemeral
                      self.not-preauthorized not-preauthorized
                      self.not-reusable not-reusable
                      self.preauthorized preauthorized
                      self.reusable reusable
                      self.tags tags
                      self.using-keys using-keys
                      self.value value
                      self.verbose verbose
                      self.properties #("ephemeral" "preauthorized" "reusable")
                      self.not-properties (tuple (gfor p self.properties (+ "not_" p)))))

          (defn t/replace [ self pt ]
                (let [tags (if self.using-keys self.value.capabilities.devices.create.tags self.value.tags)]
                     (return (cond (.startswith pt "tag:") (str (in pt tags))
                                   (.startswith pt "!tag:") (str (not (in pt tags)))
                                   True (match pt "!"              "not"
                                                  "&"              "and"
                                                  "&&"             "and"
                                                  "|"              "or"
                                                  "||"             "or"
                                                  "ephemeral"      (when self.using-keys (str self.value.capabilities.devices.create.ephemeral))
                                                  "reusable"       (when self.using-keys (str self.value.capabilities.devices.create.reusable))
                                                  "preauthorized"  (when self.using-keys (str self.value.capabilities.devices.create.preauthorized))
                                                  "!ephemeral"     (when self.using-keys (str (not self.value.capabilities.devices.create.ephemeral)))
                                                  "!reusable"      (when self.using-keys (str (not self.value.capabilities.devices.create.reusable)))
                                                  "!preauthorized" (when self.using-keys (str (not self.value.capabilities.devices.create.preauthorized)))
                                                  _                pt)))))

          (defn eval [ self group ]
                (setv source (if (isinstance group #(str bytes bytearray)) group (.join " " group))
                      tree (.parse ast source :mode "eval")
                      transformer (Transformer)
                      clause (do (.visit transformer tree) (compile tree "<AST>" "eval")))
                (return (eval clause)))

          (defn replace [ self group ]
                (let [ pts (list (intersperse self.delimiter (if self.using-keys
                                                                 (gfor pt (.flatten oreo #((gfor p self.properties (when (getattr self p)
                                                                                                                         (str (and (getattr self p)
                                                                                                                                   (getattr self.value.capabilities.devices.create p)))))
                                                                                           (gfor p self.not-properties (when (getattr self p)
                                                                                                                             (str (and (getattr self p)
                                                                                                                                       (not (getattr self.value.capabilities.devices.create p))))))
                                                                                           (when self.tags
                                                                                                 (str (all (gfor tag self.tags (in tag self.value.capabilities.devices.create.tags)))))
                                                                                           (when self.excluded-tags
                                                                                                 (str (all (gfor tag self.excluded-tags (not (in tag self.value.capabilities.devices.create.tags))))))))
                                                                       :if (not (is pt None))
                                                                       pt)
                                                                 (gfor pt #((when self.tags (str (all (gfor tag self.tags (in tag self.value.tags)))))
                                                                            (when self.excluded-tags
                                                                                  (str (all (gfor tag self.excluded-tags (not (in tag self.value.tags))))))) :if (not (is pt None)) pt))))
                       lb-split (.flatten oreo (gfor pt (.split group) (.multipart oreo pt "(")))
                       rb-split (.flatten oreo (gfor pt lb-split (.multipart oreo pt ")"))) ]
                     (yield-from (.flatten oreo #(pts
                                                  (if pts #(self.delimiter) #())
                                                  (gfor pt (filter None (.flatten oreo rb-split)) (.t/replace self pt)))))))

          (defn replace-all [ self groups ] (return (lfor group groups (.replace self group))))

          (defn t/results [ self ]
                (let [results []]
                     (when self.verbose
                           (setv dks (if self.using-keys "key" "device")
                                   of-id (if (.isnumeric self.dk) "of id " ""))
                           (print #[f[Group String{(if (= (len self.groups) 1) "" "s")} for {dks} {of-id}"{self.dk}":]f]))
                     (for [[ogroup group] (zip self.original-groups self.groups)]
                          (when self.verbose
                                (let [ group (list group)
                                       togroup "" ]
                                     (for [p self.properties]
                                          (when (getattr self p) (+= togroup f"{p} {self.delimiter} ")))
                                     (for [tag self.tags]
                                          (+= togroup f"{tag} {self.delimiter} "))
                                     (for [p self.not-properties]
                                          (when (getattr self p) (+= togroup f"{p} {self.delimiter} ")))
                                     (for [tag self.excluded-tags]
                                          (+= togroup f"!{tag} {self.delimiter} "))
                                     (+= togroup ogroup)
                                     (setv togroup (.replace togroup "not_" "!"))
                                     (+= togroup #[f[ ==> {(.join " " group)} \n]f])
                                     (print togroup)))
                             (.append results (.eval self group)))
                     (return results)))

          (defn results [ self ]
                (if self.using-keys
                    (when self.value.capabilities (yield-from (.t/results self)))
                    (yield-from (.t/results self)))))

(defclass dk-class [ Slots ]
          (defn __init__ [ self auth response-files recreate-response values excluded domain type verbose dry-run ]
                (setv self.values (or (list values) [ "all" ])
                      self.all (or (not values) (in "all" values))
                      self.all-responses (dict)
                      self.auth auth
                      self.domain domain
                      self.dry-run dry-run
                      self.excluded excluded
                      self.recreate-response recreate-response
                      self.type type
                      self.keys (= self.type "keys")
                      self.default-response-file (Path f"{(get environ "HOME")}/.local/share/tailapi/{self.domain}/{self.type}.json")
                      self.response-files (or response-files (.create-response-file-paths self self.values))
                      self.mapped (Dict (zip self.values self.response-files :strict True))
                      self.verbose verbose))

          (defn get-response [ self url error-message ] (return (return-json-addict "get" error-message url :auth self.auth)))

          (defn t/write [ self response-file response-dict ]
                (setv response-path (Path response-file)
                      response-dir (Path response-path.parent))
                (.mkdir response-dir :parents True :exist-ok True)
                (with [f (open response-file "w")]
                      (.dump json response-dict f))
                (return response-dict))

          (defn get [ self response-file [all-override False] [recreate-override False] ]
                (setv write-response (partial self.write :all-override all-override)
                      responses (cond (or self.recreate-response recreate-override) (write-response)
                                      (.exists response-file) (with [f (open response-file)]
                                                                    (Dict (.load json f)))
                                      True (write-response)))
                (when self.excluded
                      (let [ ids (dfor [k v] (.items responses) [v.id k])
                             kids (.keys ids)
                             kres (.keys responses) ]
                           (for [dk self.excluded]
                                (if (.isnumeric dk)
                                    (del (get responses (get ids (get (.extractOne process dk kids :scorer fuzz.WRatio) 0))))
                                    (del (get responses (get (.extractOne process dk kres :scorer fuzz.WRatio) 0)))))))
                (return responses))

          (defn get-all [ self [all-override False] [recreate-override False] ]
                (return (if (or self.all all-override)
                            (.get self self.default-response-file :all-override all-override :recreate-override recreate-override)
                            (Dict (dict (ChainMap #* (gfor file self.response-files (.get self file))))))))

          (defn get-ip [ self ipv4 ipv6 first ]
                (let [ both (and ipv4 ipv6)
                       responses (.get-all self)
                       ips (Dict) ]
                     (for [[dk v] (.items responses)]
                          (assoc v "addresses" (map ip-address (get v "addresses")))
                          (for [i v.addresses]
                               (if (get ips dk i.version)
                                   (.append (get ips dk i.version) i)
                                   (assoc (get ips dk) i.version [i]))))
                     (return (if ips
                                 (cond both ips
                                       ipv4 (if (= (len ips) 1)
                                                (let [ dk (next (iter ips))
                                                       ips4 (get ips dk 4) ]
                                                     (if (or first (<= (len ips4) 1)) (get ips4 0) ips4))
                                                (dfor [dk v] (.items ips) :setv v4 (get v 4) :if v4 [dk { 4 v4 }]))
                                       ipv6 (if (= (len ips) 1)
                                                (let [ dk (next (iter ips))
                                                       ips6 (get ips dk 6) ]
                                                     (if (or first (<= (len ips6) 1)) (get ips6 0) ips6))
                                                (dfor [dk v] (.items ips) :setv v6 (get v 6) :if v6 [dk { 6 v6 }]))
                                       True ips)
                                 ips))))

          (defn correct-options [ self response option ]
                (setv opts []
                      value response)
                (for [opt option]
                     (setv opt (get (.extractOne process opt (.keys value) :scorer fuzz.WRatio) 0)
                           value (get response opt))
                     (.append opts opt)
                     (else (return opts))))

          (defn getattr [ self response [option None] [joint-option None] [convert True] ]
                (let [ option (or joint-option (.join "." (.correct-options self response option)))
                       v ((attrgetter option) response) ]
                     (return (if (and convert (= option "addresses")) (map ip-address v) v))))

          (defn create-response-file-path [ self value ]
                (return (Path #[f[{(get environ "HOME")}/.local/share/tailapi/{self.domain}/{self.type}/{value}.json]f])))

          (defn create-response-file-paths [ self values ]
                (return (lfor dk values (.create-response-file-path self dk))))
  
          (defn and-or-values [ self
                                [ responses None ]
                                [ tags #() ]
                                [ excluded-tags #() ]
                                [ groups #() ]
                                [ or-pt False ]
                                [ ephemeral False ]
                                [ not-ephemeral False ]
                                [ reusable False ]
                                [ not-reusable False ]
                                [ preauthorized False ]
                                [ not-preauthorized False ] ]
                (let [ responses (or responses (.get-all self))
                       values []
                       tags (sfor tag tags :if (not (.startswith tag "tag:")) (+ "tag:" tag))
                       excluded-tags (sfor tag excluded-tags :if (not (.startswith tag "tag:")) (+ "tag:" tag))
                       variables { "tags" tags
                                   "excluded_tags" excluded-tags
                                   "ephemeral" ephemeral
                                   "not_ephemeral" not-ephemeral
                                   "reusable" reusable
                                   "not_reusable" not-reusable
                                   "preauthorized" preauthorized
                                   "not_preauthorized" not-preauthorized
                                   "groups" groups }
                       group-partial (partial Group :using-keys self.keys
                                                    :verbose self.verbose
                                                    #** variables) ]
                     (when (any (.values variables))
                           (if or-pt
                               (for [[dk v] (.items responses)]
                                    (let [ group (group-partial :delimiter "or" :dk dk :value v) ]
                                         (if self.keys
                                             (when (and v.capabilities 
                                                        (any #((and ephemeral v.capabilities.devices.create.ephemeral)
                                                               (and not-ephemeral (not v.capabilities.devices.create.ephemeral))
                                                               (and preauthorized v.capabilities.devices.create.preauthorized)
                                                               (and not-preauthorized (not v.capabilities.devices.create.preauthorized))
                                                               (and reusable v.capabilities.devices.create.reusable)
                                                               (and not-reusable (not v.capabilities.devices.create.reusable))
                                                               (any (.results group))
                                                               (any (gfor tag tags (in tag v.capabilities.devices.create.tags)))
                                                               (any (gfor tag excluded-tags (not (in tag v.capabilities.devices.create.tags)))))))
                                                   (.append values dk))
                                             (when (any #((any (.results group))
                                                          (any (gfor tag tags (in tag v.tags)))
                                                          (any (gfor tag excluded-tags (not (in tag v.tags))))))
                                                   (.append values dk)))))
                               (for [[dk v] (.items responses)]
                                    (let [ group (group-partial :delimiter "and" :dk dk :value v) ]
                                         (if self.keys
                                             (when (and v.capabilities
                                                        (all (gfor n #((when ephemeral (and ephemeral v.capabilities.devices.create.ephemeral))
                                                                       (when not-ephemeral (and not-ephemeral (not v.capabilities.devices.create.ephemeral)))
                                                                       (when preauthorized (and preauthorized v.capabilities.devices.create.preauthorized))
                                                                       (when not-preauthorized (and not-preauthorized (not v.capabilities.devices.create.preauthorized)))
                                                                       (when reusable (and reusable v.capabilities.devices.create.reusable))
                                                                       (when not-reusable (and not-reusable (not v.capabilities.devices.create.reusable)))
                                                                       (when groups (all (.results group)))
                                                                       (when tags (all (gfor tag tags (in tag v.capabilities.devices.create.tags))))
                                                                       (when excluded-tags (all (gfor tag excluded-tags (not (in tag v.capabilities.devices.create.tags))))))
                                                                   :if (not (is n None))
                                                                   n)))
                                                   (.append values dk))
                                             (when (all (gfor n #((when groups (all (.results group)))
                                                                  (when tags (all (gfor tag tags (in tag v.tags))))
                                                                  (when excluded-tags (all (gfor tag excluded-tags (not (in tag v.tags))))))
                                                              :if (not (is n None))
                                                              n))
                                                   (.append values dk)))))))
                     (return values)))

          (defn t/delete [ self url success-message error-message [ignore-error False] ]
                (let [ response (.delete requests url :auth self.auth) ]
                     (if (= (getattr response "status_code") 200)
                         (do (print success-message)
                             (return True))
                         (if ignore-error
                             (return False)
                             (raise-response-error error-message response)))))

          (defn t/delete-all [ self [values None] [ignore-error False] ]
                (try (for [dk (or values (.get-all self))]
                          (when (.delete self dk :ignore-error ignore-error)
                                (when (in dk self.values) (.remove self.values dk))
                                (when (in dk self.mapped) (.remove self.response-files (.pop self.mapped dk)))))
                     (finally (.write self)
                              (unless self.all (.write self :all-override True)))))

          (defn delete-all [ self
                             [ responses None ]
                             [ do-not-prompt False ]
                             [ or-pt False ]
                             [ tags #() ]
                             [ excluded-tags #() ]
                             [ ephemeral False ]
                             [ not-ephemeral False ]
                             [ reusable False ]
                             [ not-reusable False ]
                             [ preauthorized False ]
                             [ not-preauthorized False ]
                             [ groups #() ]
                             [ ignore-error False ] ]
                (let [ responses (or responses (.get-all self))
                       values (.and-or-values self :responses responses
                                                   :tags tags
                                                   :excluded-tags excluded-tags
                                                   :groups groups
                                                   :or-pt or-pt
                                                   :ephemeral ephemeral
                                                   :not-ephemeral not-ephemeral
                                                   :reusable reusable
                                                   :not-reusable not-reusable
                                                   :preauthorized preauthorized
                                                   :not-preauthorized not-preauthorized)
                       all-your-specified (if self.all "ALL YOUR" "THE SPECIFIED")
                       devices-or-keys (if self.keys "AUTHKEYS" "DEVICES")
                       vr-string (.join " " (or values (.keys responses)))
                       input-message f"THIS WILL DELETE {all_your_specified} {devices_or_keys} [ {vr-string} ] FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN \"DELETE {devices_or_keys}\" WITHOUT THE QUOTES:\n\t"
                       input-response f"DELETE {devices_or_keys}" ]
                     (when self.verbose
                           (print "Key Dictionary:")
                           (pprint responses)
                           (print "\nKeys to be deleted: ")
                           (print values))
                     (when (and (not self.dry-run) (or do-not-prompt (= (input input-message) input-response)))
                           (.t/delete-all self :values values :ignore-error ignore-error))))

          (defn filterattrs [ self options [responses None] [convert True] ]
                (let [ responses (if (is responses None) (.get-all self) responses) ]
                     (if options
                         (let [ new-responses (Dict (zip (.keys responses) (* [{}] (len responses)))) ]
                              (for [[k v] (.items new-responses) option options]
                                   (let [ response (get responses k)
                                          joint-option (.join "." (.correct-options self response (.split option "."))) ]
                                        (.set magicattr v joint-option (.getattr self response :joint-option joint-option :convert convert))))
                              (return new-responses))
                         (return responses))))

          (defn filter [ self
                         [ options #() ]
                         [ convert True ]
                         [ responses None ]
                         [ api-keys False ]
                         [ or-pt False ]
                         [ tags #() ]
                         [ excluded-tags #() ]
                         [ ephemeral False ]
                         [ not-ephemeral False ]
                         [ reusable False ]
                         [ not-reusable False ]
                         [ preauthorized False ]
                         [ not-preauthorized False ]
                         [ groups #() ] ]
                (if (and api-keys self.keys)
                    (return (.get-api-keys self :verbose True))
                    (let [ responses (or responses (.get-all self))
                           values (.and-or-values self :responses responses
                                                       :tags tags
                                                       :excluded-tags excluded-tags
                                                       :groups groups
                                                       :or-pt or-pt
                                                       :ephemeral ephemeral
                                                       :not-ephemeral not-ephemeral
                                                       :reusable reusable
                                                       :not-reusable not-reusable
                                                       :preauthorized preauthorized
                                                       :not-preauthorized not-preauthorized)]
                           (return (.filterattrs self
                                                 options
                                                 :responses (dfor value values [ value (get responses value) ])
                                                 :convert convert))))))

(defclass device-class [ dk-class ]
          (defn __init__ [ self recreate-response response-files auth values domain excluded verbose dry-run ]
                (.__init__ (super) :values values :auth auth :response-files response-files :recreate-response recreate-response :excluded excluded :domain domain :type "devices" :verbose verbose :dry-run dry-run))

          (defn write [ self [all-override False] ]
                (if (or self.all all-override)
                    (do (setv devices (get (.get-response self f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/{self.type}?fields=all"
                                                               f"Sorry; something happened when trying to get all {self.type}!") self.type)
                              all-responses (Dict (dfor device devices [ (get (.split (get device "name") ".") 0) device ])))
                        (.t/write self self.default-response-file all-responses))
                    (do (setv all-responses (Dict))
                        (for [[device file] (.items self.mapped)]
                             (if (.isnumeric device)
                                 (do (setv response (.get-response self f"https://api.tailscale.com/api/v2/device/{device}?fields=all",
                                                                        #[f[Sorry; something happened when trying to get device of id "{device}"!]f]))
                                     (.update all-responses (.t/write self file { (get (.split (get response "name") ".") 0) response })))
                                 (do (setv self.all-responses (or self.all-responses (.get-all self :all-override True)))
                                     (.update all-responses (.t/write self file { device (get self.all-responses device) })))))))
                (return all-responses))

          (defn delete [ self device [ignore-error False] ]
                (if (.isnumeric device)
                    (setv id device
                          of-id "of id ")
                    (setv self.all-responses (or self.all-responses (.get-all self :all-override True :recreate-override True))
                          id (get self.all-responses device "id")
                          of-id ""))
                (return (.t/delete self f"https://api.tailscale.com/api/v2/device/{id}"
                                        #[f[Sucessfully deleted device {of_id}"{device}"!]f]
                                        #[f[Sorry; something happened when trying to delete device {of_id}"{device}"!]f]
                                        :ignore-error ignore-error))))

(defclass key-class [ dk-class ]
          (defn __init__ [ self values response-files auth recreate-response domain excluded verbose dry-run ]
                (.__init__ (super) :values values :auth auth :response-files response-files :recreate-response recreate-response :excluded excluded :domain domain :type "keys" :verbose verbose :dry-run dry-run))

          (defn create-url [ self key ] (return f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/{self.type}/{key}"))

          (defn write [ self [ all-override False ] ]
                (setv all-responses (Dict))
                (if (or self.all all-override)
                    (do (for [key (get (.get-response self f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/{self.type}"
                                                           f"Sorry; something happened when trying to get all {self.type}!") self.type)]
                             (assoc all-responses (get key "id") (.get-response self (.create-url self (get key "id"))
                                                                                     #[f[Sorry; something happened when trying to get key of id "{key}"!]f])))
                        (.t/write self self.default-response-file all-responses))
                    (for [[key file] (.items self.mapped)]
                         (let [ response (.get-response self (.create-url self key) #[f[Sorry; something happened when trying to get key of id "{key}"!]f]) ]
                              (.update all-responses (.t/write self file { (get response "id") response })))))
                (return all-responses))

          (defn delete [ self key [ignore-error False] ]
                (if (in key (.get-api-keys self))
                    (do (print "Sorry; not deleting an API key!")
                        (return False))
                    (return (.t/delete self f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/{self.type}/{key}"
                                            #[f[Sucessfully deleted key of id "{key}"!]f]
                                            #[f[Sorry; something happened when trying to delete key of id "{key}"!]f]
                                            :ignore-error ignore-error))))

          (defn create-key [ self [ ephemeral False ] [ preauthorized False ] [ reusable False ] [ tags #() ] [ print-key False ] ]
                (setv data (Dict)
                      data.capabilities.devices.create { "ephemeral" ephemeral
                                                         "preauthorized" preauthorized
                                                         "reusable" reusable
                                                         "tags" (list (sfor tag tags :if (not (.startswith tag "tag:")) (+ "tag:" tag))) }
                      response (return-json-addict "post"
                                                   #[f[Sorry; something happened when trying to create a key with the following properties: "{data}"!]f]
                                                   f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/{self.type}"
                                                   :json data
                                                   :auth self.auth))
                (return response))

          (defn get-api-keys [ self [ verbose False ] ]
                (return (if verbose
                            (dfor [k v] (.items (.get-all self :all-override True)) :if (not v.capabilities) [ k v ])
                            (lfor [k v] (.items (.get-all self :all-override True)) :if (not v.capabilities) k)))))

(setv tailscale-domain (.get environ "TAILSCALE_DOMAIN" :default None)
      tailscale-api-key (.get environ "TAILSCALE_APIKEY" :default None))
(defn [ (.group click :no-args-is-help True)
        (.option click "-a" "--api-key" :required (not tailscale-api-key) :default tailscale-api-key)
        (.option click "-d"
                       "--devices"
                       :cls oreo.Option
                       :help "The device name or id; input `all' to show all devices, or specify multiple times for multiple devices.
Every index here matches to the same index in `--device-response-files', while a value of `all' uses a single file.
If no device response files are given, the device names are used for all specified devices."
                       :multiple True
                       :xor #("keys"))
        (.option click "-D" "--domain" :required (not tailscale-domain) :default tailscale-domain)
        (.option click "-k"
                       "--keys"
                       :cls oreo.Option
                       :help "The key id; input `all' to show all keys, or specify multiple times for multiple keys.
Every index here matches to the same index in `--key-response-files', while a value of `all' uses a single file.
If no key response files are given, the key ids' are used for all specified keys."
                       :multiple True
                       :xor #("devices"))
        (.option click "-K"
                       "--all-keys"
                       :is-flag True
                       :cls oreo.Option
                       :help "Show all keys."
                       :xor #("devices" "keys"))
        (.option click "-f"
                       "--device-response-files"
                       :help "Where the device information should be stored;
every index here matches to the same index in `--devices', while a value of `all' in `--devices' uses a single file."
                       :multiple True)
        (.option click "-F"
                       "--key-response-files"
                       :help "Where the device information should be stored;
every index here matches to the same index in `--keys', while a value of `all' in `--keys' uses a single file."
                       :multiple True)
        (.option click "-e" "--excluded" :multiple True)
        (.option click "-r" "--recreate-response" :is-flag True)
        (.option click "-n" "--dry-run" :is-flag True)
        (.option click "-v" "--verbose" :is-flag True)
        click.pass-context ]
      tailapi [ ctx
                all-keys
                api-key
                domain
                devices
                device-response-files
                key-response-files
                recreate-response
                keys
                dry-run
                verbose
                excluded ]
      (.ensure-object ctx dict)
      (setv type- (if (or all-keys keys (= ctx.invoked-subcommand "create")) "key" "device")
            ctx.obj.cls ((eval (+ type- "_class")) :auth (HTTPBasicAuth api-key "")
                                                   :domain domain
                                                   :recreate-response recreate-response
                                                   :excluded excluded
                                                   :verbose verbose
                                                   :dry-run dry-run
                                                   :values (eval (+ type- "s"))
                                                   :response-files (eval (+ type- "_response_files")))))

(defn [ (.command tailapi)
        (.argument click "options" :nargs -1 :required False)
        click.pass-context ]
      show [ctx options]
      "OPTIONS: Print a dictionary of (nested) options for the specified devices or keys."
      (.cprint oreo (.filterattrs ctx.obj.cls options :convert False)))

(defn [ (.command tailapi :no-args-is-help True :name "get")
        (.argument click "option" :nargs -1)
        click.pass-context ]
      t/get [ctx option]
      "OPTION: Print a (nested) option for the specified devices or keys."
      (let [ responses (.get-all ctx.obj.cls) ]
           (for [dk responses] (.cprint oreo (.getattr ctx.obj.cls (get responses dk) :option option :convert False)))))

(defn [ (.command tailapi)
        (.option click "-4" "--ipv4" :is-flag True)
        (.option click "-6" "--ipv6" :is-flag True)
        (.option click "-f" "--first" :is-flag True)
        click.pass-context ]
      ip [ctx ipv4 ipv6 first]
      (let [ ips (.get-ip ctx.obj.cls ipv4 ipv6 first) ]
           (if (isinstance ips list)
               (print (.join "\n" ips))
               (.cprint oreo ips))))

(defn [ (.command tailapi :name "filter")
        (.argument click "options" :nargs -1 :required False)
        (.option click "-t" "--tags" :multiple True)
        (.option click "-T" "--excluded-tags" :multiple True)
        (.option click "-e" "--ephemeral" :is-flag True)
        (.option click "-E" "--not-ephemeral" :is-flag True)
        (.option click "-p" "--preauthorized" :is-flag True)
        (.option click "-P" "--not-preauthorized" :is-flag True)
        (.option click "-r" "--reusable" :is-flag True)
        (.option click "-R" "--not-reusable" :is-flag True)
        (.option click "-A" "--api-keys" :is-flag True :help "Print the API keys.")
        (.option click "-a"
                       "--and-pt"
                       :cls oreo.Option
                       :xor #("or-pt")
                       :is-flag True
                       :help "If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with all of the specified tags and properties.
Note that properties don't work with devices. This is the default.")
        (.option click "-o"
                       "--or-pt"
                       :cls oreo.Option
                       :xor #("and-pt")
                       :is-flag True
                       :help "If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with any of the specified tags and properties. Note that properties don't work with devices.")
        (.option click "-g"
                       "--groups"
                       :multiple True
                       :help "Strings of properties and tags following boolean logic (`&&', `&', or `and', and `||', `|', or `or'),
such as `(ephemeral or reusable) and (tag:server or tag:relay)' deleting all keys with the ephemeral or reusable properties,
and with the server or relay tags.
Can be specified multiple times, where `--or-pt' and `--and-pt' will be used to dictate the interactions between groups,
and can be used with other property and tag options, such as `--ephemeral', etc.
Negation can be achieved with `!' prefixed to the properties or tags, such as `!ephemeral' or `!tag:server'. Note that properties don't work with devices.")
        click.pass-context ]
      t/filter [ ctx
                 api-keys
                 and-pt
                 or-pt
                 tags
                 excluded-tags
                 ephemeral
                 not-ephemeral
                 preauthorized
                 not-preauthorized
                 reusable
                 not-reusable
                 groups
                 options ]
      "OPTIONS: Print a dictionary of (nested) options for the filtered devices or keys."
      (.cprint oreo (.filter ctx.obj.cls
                             :options options
                             :convert False
                             :api-keys api-keys
                             :or-pt or-pt
                             :tags tags
                             :excluded-tags excluded-tags
                             :ephemeral ephemeral
                             :not-ephemeral not-ephemeral
                             :preauthorized preauthorized
                             :not-preauthorized not-preauthorized
                             :reusable reusable
                             :not-reusable not-reusable
                             :groups groups)))

(defn [ (.command tailapi)
        (.option click "-t" "--tags" :multiple True)
        (.option click "-T" "--excluded-tags" :multiple True)
        (.option click "--do-not-prompt" :is-flag True)
        (.option click "-i" "--ignore-error" :is-flag True)
        (.option click "-e" "--ephemeral" :is-flag True)
        (.option click "-E" "--not-ephemeral" :is-flag True)
        (.option click "-r" "--reusable" :is-flag True)
        (.option click "-R" "--not-reusable" :is-flag True)
        (.option click "-p" "--preauthorized" :is-flag True)
        (.option click "-P" "--not-preauthorized" :is-flag True)
        (.option click "-a"
                       "--and-pt"
                       :cls oreo.Option
                       :xor #("or-pt")
                       :is-flag True
                       :help "If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with all of the specified tags and properties.
Note that properties don't work with devices. This is the default.")
        (.option click "-o"
                       "--or-pt"
                       :cls oreo.Option
                       :xor #("and-pt")
                       :is-flag True
                       :help "If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with any of the specified tags and properties. Note that properties don't work with devices.")
        (.option click "-g"
                       "--groups"
                       :multiple True
                       :help "Strings of properties and tags following boolean logic (`&&', `&', or `and', and `||', `|', and `or'),
such as `(ephemeral or reusable) and (tag:server or tag:relay)' deleting all keys with the ephemeral or reusable properties,
and with the server or relay tags.
Can be specified multiple times, where `--or-pt' and `--and-pt' will be used to dictate the interactions between groups,
and can be used with other property and tag options, such as `--ephemeral', etc.
Negation can be achieved with `!' prefixed to the properties or tags, such as `!ephemeral' or `!tag:server'. Note that properties don't work with devices.")
        click.pass-context ]
      delete [ ctx
               do-not-prompt
               ignore-error
               and-pt
               or-pt
               tags
               excluded-tags
               ephemeral
               not-ephemeral
               reusable
               not-reusable
               preauthorized
               not-preauthorized
               groups ]
      (.delete-all ctx.obj.cls :do-not-prompt do-not-prompt
                               :ignore-error ignore-error
                               :or-pt or-pt
                               :tags tags
                               :excluded-tags excluded-tags
                               :ephemeral ephemeral
                               :not-ephemeral not-ephemeral
                               :preauthorized preauthorized
                               :not-preauthorized not-preauthorized
                               :reusable reusable
                               :not-reusable not-reusable
                               :groups groups))

(defn [ (.command tailapi :no-args-is-help True)
        (.argument click "tags" :nargs -1 :required False)
        (.option click "-e" "--ephemeral" :is-flag True)
        (.option click "-p" "--preauthorized" :is-flag True)
        (.option click "-r" "--reusable" :is-flag True)
        (.option click "-j" "--just-key" :is-flag True :help "Just print the key.")
        (.option click "-c" "--count" :cls oreo.Option :xor #("groups") :default 1 :type int :help "Number of keys to create.")
        (.option click "-g"
                       "--groups"
                       :cls oreo.Option
                       :xor #("count")
                       :multiple True
                       :help "Strings of properties and tags,
such as `ephemeral reusable tag:relay tag:server' creating an ephemeral and reusable key with tags `relay' and `server'.
If used with other property options, such as `--preauthorized', or tag arguments, all keys will have those properties and tags as well.
Note that tags here must be prefixed with `tag:'.")
        click.pass-context ]
      create [ ctx tags ephemeral preauthorized reusable just-key count groups ]
      "TAGS: Note that tags here do not need to be prefixed with `tag:'."
      (setv tags (set tags))
      (if groups
          (for [group groups]
               (let [ split-group (.split group)
                      response (.create-key ctx.obj.cls :ephemeral (or (in "ephemeral" split-group) ephemeral)
                                                        :preauthorized (or (in "preauthorized" split-group) preauthorized)
                                                        :reusable (or (in "reusable" split-group) reusable)
                                                        :tags (| (sfor tag split-group :if (.startswith tag "tag:") tag) tags)) ]
                    (.cprint oreo (if just-key response.key response))))
          (for [i (range count)]
               (let [ response (.create-key ctx.obj.cls :ephemeral ephemeral
                                                        :preauthorized preauthorized
                                                        :reusable reusable
                                                        :tags tags) ]
                    (.cprint oreo (if just-key response.key response))))))