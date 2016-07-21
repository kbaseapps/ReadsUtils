
package us.kbase.readsutils;

import java.util.HashMap;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: ConvertReadLibraryOutput</p>
 * <pre>
 * The output of the convert method.
 * mapping<read_lib, ConvertedReadLibrary> files - a mapping
 *     of the read library workspace references to information
 *     about the converted data for each library.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "files"
})
public class ConvertReadLibraryOutput {

    @JsonProperty("files")
    private Map<String, ConvertedReadLibrary> files;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("files")
    public Map<String, ConvertedReadLibrary> getFiles() {
        return files;
    }

    @JsonProperty("files")
    public void setFiles(Map<String, ConvertedReadLibrary> files) {
        this.files = files;
    }

    public ConvertReadLibraryOutput withFiles(Map<String, ConvertedReadLibrary> files) {
        this.files = files;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((("ConvertReadLibraryOutput"+" [files=")+ files)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
